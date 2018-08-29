from html.parser import HTMLParser
import json
from medium_to_ghost.image_downloader import download_image_with_local_cache
from bs4 import BeautifulSoup
import logging
from pathlib import Path


def parse_medium_filename(filename):
    status = "published"

    date, slug = filename.split("_")
    slug = slug.split(".")[0]
    slug_parts = slug.split("-")
    uuid = slug_parts[-1]
    slug = "-".join(slug_parts[0:-1])

    # Determine if the post is a draft or is live based on the export's filename
    # If the date in the filename is "draft", it's unpublished. Otherwise filename has a pub date.
    if date == "draft":
        status = "draft"
        date = None

    return uuid, slug, date, status


def convert_medium_post_to_ghost_json(html_filename, post_html_content):
    """
    Convert a Medium HTML export file's content into a Mobiledoc document.
    :param html_filename: The original filename from Medium (needed to grab publish state)
    :param post_html_content: The html body (string) of the post itself
    :return: Python dictionary representing a Mobiledoc version of this post
    """
    logging.info(f"Parsing {html_filename}")

    # Get the publish date and slug from the exported filename
    _, filename = html_filename.split("/")
    uuid, slug, date, status = parse_medium_filename(filename)

    # Extract post-level metadata elements that will be at known elements
    soup = BeautifulSoup(post_html_content, 'html.parser')

    # - Article Title
    title = soup.find("h1", {"class": "p-name"}).text
    # - Subtitle
    subtitle = soup.find("section", {"class": "p-summary"}).text if soup.find("section", {"class": "p-summary"}) else None

    # Medium stores every comment as full story.
    # Guess if this post was a comment or a post based on if it has a post title h3 or not.
    # If it seems to be a comment, skip converting it since we have no idea what it was a comment on.
    title_el = soup.find("h3", {"class": "graf--title"})

    # Hack: Some really old Medium posts used h2 instead of h3 for the title element.
    if not title_el:
        title_el = soup.find("h2", {"class": "graf--title"})

    # If there's no title element, this document is probably a comment. Skip!
    if title_el is None:
        logging.warning(f"Skipping {html_filename} because it appears to be a Medium comment, not a post!")
        return None

    # All the remaining document-evel attributes we need to collect
    comment_id = None
    plain_text = None
    feature_image = None
    created_at = date
    updated_at = date
    published_at = date
    custom_excerpt = subtitle

    # Convert story body itself to mobiledoc format (As required by Ghost)
    parser = MediumHTMLParser()
    parser.feed(post_html_content)
    mobiledoc_post = parser.convert()

    # Download all the story's images to local disk cache folder
    for card in mobiledoc_post["cards"]:
        card_type = card[0]
        if card_type == "image":
            data = card[1]
            url = data["src"]

            cache_folder = Path("exported_content") / "downloaded_images" / slug
            new_image_path = download_image_with_local_cache(url, cache_folder)

            # TODO: Fix this when Ghost fixes https://github.com/TryGhost/Ghost/issues/9821
            # Ghost 2.0.3 has a bug where it doesn't update imported image paths, so manually add
            # /content/images.
            final_image_path_for_ghost = str(new_image_path).replace("exported_content", "/content/images")
            data["src"] = final_image_path_for_ghost

            # If this image was the story's featured image, grab it.
            # Confusingly, post images ARE updated correctly in 2.0.3, so this path is different
            if "featured_image" in data:
                del data["featured_image"]
                feature_image = str(new_image_path).replace("exported_content", "")


    # Create the final post dictionary as required by Ghost 2.0
    return {
        # "id": id,
        "uuid": uuid,
        "title": title,
        "slug": slug,
        "mobiledoc": json.dumps(mobiledoc_post),
        "html": post_html_content,
        "comment_id": comment_id,
        "plaintext": plain_text,
        "feature_image": feature_image,
        "featured": 0,
        "page": 0,
        "status": status,
        "locale": None,
        "visibility": "public",
        "meta_title": None,
        "meta_description": None,
        "author_id": "1",
        "created_at": created_at,
        "created_by": "1",
        "updated_at": updated_at,
        "updated_by":  "1",
        "published_at": published_at,
        "published_by": "1",
        "custom_excerpt": custom_excerpt,
        "codeinjection_head": None,
        "codeinjection_foot": None,
        "custom_template": None,

        # These all inherit from the metadata title/description in Ghost, so no need to set them explicitly
        "og_image": None,
        "og_title": None,
        "og_description": None,
        "twitter_image": None,
        "twitter_title": None,
        "twitter_description": None,
    }


class MediumHTMLParser(HTMLParser):
    """
    This Parser takes in an HTML file produced by Medium's data export function and converts it to an
    equivalent MobileDoc representation.

    Warning: This code is pretty crappy and hacked out quickly to work for the needs of Mediumm files. It definitely
    won't work as a Mobiledoc converter for arbitrary HTML files.
    """
    def __init__(self):
        super().__init__()

        # Document state variables required by the Mobiledoc format that we need to accumulate as we parse the HTML doc
        self.sections = []
        self.markups = [
            # Default mobiledoc markups we'll always need for Medium docs, so we'll hard-code them as the first
            # markup elements in the final Mobiledoc file.
            ["em"],
            ["strong"]
        ]
        self.atoms = []
        self.cards = []

        # Temporary parse state variables to keep track of where we are as we parse each HTML tag
        self.current_markers = []
        self.current_list_item_markers = []
        self.tag_stack = []

        # Medium export files start every post with an extra <hr> and the title inline as an <h3>
        # We don't want to include either in the data that goes to Ghost
        self.seen_first_h3 = False
        self.seen_first_hr = False

        # Medium exports include junk in the <footer>. Ignore everything in the footer.
        self.seen_footer = False

        # Medium exports can include link summary cards that are divs with a "graf" class
        self.inside_link_summary_div = False

        # Medium breaks code blocks and blockquotes with embedded returns into separate tags. Need to track
        # if the previous block was a <pre> or <blockquote> so we can join them back together. Otherwise the
        # exported Mobiledoc file will look crappy.
        self.last_section_tag = None

    def attrs_to_dict(self, attrs):
        """
        Convert an html attrs list into a dict
        :param attrs: list of sequential attrs from an HTML parser
        :return: Dict with attr: value
        """
        return {k: v for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        """
        Handle an HTML opening tag with it's attrs.
        :param tag: current HTML tag we are att
        :param attrs: any html attributes given in the html tag
        :return: None
        """

        # Medium export files have a footer with junk that's not part of the original post.
        # Stop processing entirely if we hit the document footer.
        if self.seen_footer:
            return
        if tag == "footer":
            self.seen_footer = True

        # Keep track of where we are in the DOM by putting this tag on a stack
        self.tag_stack.append(tag)

        # Convert any html tag attributes to a dictionary just so they are easier to look up.
        attr_dict = self.attrs_to_dict(attrs)

        # In Mobiledoc format, the 'parent' elements of a doc can be one of a fixed set of tags:
        # - p
        # - h1, h2, h3, h4, h5, h6
        # - blockquote
        # - ul or ol
        # So when we hit one of these tags in a Medium html, we'll start accumulating child Mobiledoc elements of this element.
        if tag in ["p", "h1", "h2", "h3", "h4", "blockquote", "ul", "ol", "div"]:
            # State variables to accumulate child Mobiledoc elements of this tag.
            # We assume Medium html doc never have more than one of these parent elements at a time, so these
            # variables just keep track of the children of the single current parent element.
            # This won't work for arbitrary html files not produced by Medium.
            self.current_markers = []
            self.current_list_item_markers = []

            if tag == "div" and "class" in attr_dict and "graf" in attr_dict["class"]:
                self.inside_link_summary_div = True
        else:
            # Otherwise, we have one of the many possible kinds of child elements. We need to convert each into
            # an equivalent Mobiledoc representation and add it to the current parent element.

            # <a href=''> HTML links turn into Mobiledoc 'markup' elements with href data
            if tag == "a":
                markup = [
                    "a",
                    [
                        "href",
                        attr_dict["href"]
                    ]
                ]
                self.markups.append(markup)

            # <img> turn into Mobiledoc 'card' elements with src data. They *could* be 'markup' elements but
            # cards are recommended in Ghost with the new editor.
            # We can also find the post's featured image and guess if the image was displayed as 'wide' on medium and
            # replicate that on Ghost.
            elif tag == "img":
                image_attributes = {
                    "src": attr_dict["src"]
                }

                # Even though medium doesn't include image display width in the export,
                # you can guess that the image was shown wide based on the size of the CDN image it links to.
                if "/max/1000/" in attr_dict["src"]:
                    image_attributes["cardWidth"] = "wide"

                # Check if this was the medium post's featured image.
                # If it was, we definitely want to save that off as document metadata.
                if "data-is-featured" in attr_dict and attr_dict["data-is-featured"] == "true":
                    image_attributes["featured_image"] = True

                card = [
                    'image',
                    image_attributes
                ]
                self.cards.append(card)

                # 10 in Mobiledoc is the magic number for 'Card'
                section = [10, len(self.cards) - 1]
                self.sections.append(section)

            # <pre> turn into Mobiledoc code 'card' elements with code content data. They *could* be 'markup' elements but
            # cards are recommended in Ghost with the new editor.
            # We also have to deal with the issue that Medium makes each line of code a new <pre> tag. So if the last
            # element was a <pre>, just keep appending to the last card instead of creating a new one.
            elif tag == "pre":
                # If the last tag wasn't a <pre>, create a new code block
                if self.last_section_tag != "pre":
                    card = [
                        'code',
                        {"code": ""}
                    ]
                    self.cards.append(card)

                    # 10 in Mobiledoc is the magic number for 'Card'
                    section = [10, len(self.cards) - 1]
                    self.sections.append(section)
                else:
                    # If the last section was a <pre>, just keep appending.
                    # We also need to add a line break between each appended <pre> to maintain formatting..
                    self.cards[-1][1]["code"] += "\n\n"

            # Some Medium embeds become <iframe> tags in the export file.
            # This includes things like embedded subscription forms or some kinds of external content.
            # <iframe> tags turn into Mobiledoc card elements with an <iframe> tag that links to the same place as before.
            elif tag == "iframe":
                # Generate an <iframe> tag in text that replicates the original on in the Medium export
                attr_strings = []
                for k, v in attr_dict.items():
                    attr_strings.append(f'{k}="{v}"')
                attr_string = " ".join(attr_strings)
                html_markup = f"<iframe {attr_string}></iframe>"

                # Create the Mobiledoc Card
                card = [
                    'html',
                    {"html": html_markup}
                ]
                self.cards.append(card)

                # 10 in Mobiledoc is the magic number for 'Card'
                section = [10, len(self.cards) - 1]
                self.sections.append(section)

            # Handle Github gists in the Medium doc. They appear in the export as <script> tags.
            # So we'll create a Mobiledoc card element with a <script> tag that links to the same place as before.
            elif tag == "script" and "gist.github.com" in attr_dict["src"]:
                # Handle embedded gists
                attr_strings = []
                for k, v in attr_dict.items():
                    attr_strings.append(f'{k}="{v}"')
                attr_string = " ".join(attr_strings)
                html_markup = f"<script {attr_string}></script>"
                card = [
                    'html',
                    {"html": html_markup}
                ]
                self.cards.append(card)

                # 10 in Mobiledoc is the magic number for 'Card'
                section = [10, len(self.cards) - 1]
                self.sections.append(section)

            # <hr> tags become special "hr" cards in Mobiledoc.
            # We also need to skip the first <hr> because Medium adds an extra one at the top of every exported doc.
            elif tag == "hr":
                if self.seen_first_hr:
                    card = ["hr", {}]
                    self.cards.append(card)

                    # 10 in Mobiledoc is the magic number for 'Card'
                    section = [10, len(self.cards) - 1]
                    self.sections.append(section)
                self.seen_first_hr = True


            # <br> tags translate to different Mobiledoc elements depending on their context
            elif tag == "br":
                # We know Medium's <br> tags never have a matching closing tag, so remove this element from the stack.
                self.tag_stack.pop()

                if "pre" in self.tag_stack:
                    # - A <br> in a <pre> just needs to be appeneded to the current code block as a line break
                    self.cards[-1][1]["code"] += "\n"
                else:
                    # - A <br> inside a <p>, <blockquote>, etc needs to be converted to a Mobiledoc "soft-return" atom.
                    atom = ["soft-return", "", {}]
                    self.atoms.append(atom)

                    # Add a mobiledoc element to point to that new mobiledoc atom
                    marker = [1, [], 0, len(self.atoms) - 1]
                    self.current_markers.append(marker)


    def handle_endtag(self, tag):
        """
        Handle an HTML closing tag.
        NOTE: This never gets called if the html tag doesn't have a closing tag (i.e. <br>, <img>, etc)
        :param tag: current HTML tag we are closing
        :return: None
        """
        # Medium export files have a footer with junk that's not part of the original post.
        # Stop processing entirely if we hit the document footer.
        if self.seen_footer:
            return

        # Some html tags can be converted to Mobiledoc just based on their opening html tag.
        # However, these elements all need to be handled on the closing tag because they wrap document content.

        # Get the running list of child elements we've accumulated so far.
        markers = self.current_markers

        # Handle each kind of parent element by converting it to an equivalent Mobiledoc element and putting all the
        # current child elements under it
        if tag == "p":
            section = [1, "p", markers]
            self.sections.append(section)
        if tag == "div" and self.inside_link_summary_div:
            self.inside_link_summary_div = False
            section = [1, "p", markers]
            self.sections.append(section)
        elif tag == "li":
            self.current_list_item_markers.append(markers)
            self.current_markers = []
        elif tag == "ul":
            section = [3, "ul", self.current_list_item_markers]
            self.sections.append(section)
        elif tag == "ol":
            section = [3, "ol", self.current_list_item_markers]
            self.sections.append(section)
        elif tag == "blockquote":
            # If the last section was a blockquote, appened. Otherwise, make a new one.
            if self.last_section_tag != "blockquote":
                section = [1, "blockquote", markers]
                self.sections.append(section)
            else:
                atom = ["soft-return", "", {}]
                self.atoms.append(atom)

                marker = [1, [], 0, len(self.atoms) - 1]
                markers.append(marker)

                self.sections[-1][2] += markers
        elif tag == "h3":
            # Need to throw away the first h3 because Medium includes the Post tile in the document itself
            # but Ghost adds that. If we don't do this, each Ghost post will be displayed with the title twice.
            if self.seen_first_h3:
                # An h3 in Medium == an h2 in Ghost, so translate that
                section = [1, "h2", markers]
                self.sections.append(section)
            self.seen_first_h3 = True
        elif tag == "h4":
            # An h4 in Medium == an h3 in Ghost, so translate that
            section = [1, "h3", markers]
            self.sections.append(section)

        # Keep track of the last parent element we saw so we can combine multiple sequential <blockquote> elements.
        if tag in ["p", "blockquote", "h3", "h4", "pre", "ol", "ul", "div"]:
            self.last_section_tag = tag

        # Keep track of where we are in the DOM by popping this tag off the stack.
        # However, this function never gets closed for tags that don't have matching closing tags like
        # <img> and <br>, so we need to clear any of those out above this tag in the stack too.
        while self.tag_stack[-1] != tag and ("br" in self.tag_stack or "img" in self.tag_stack):
            self.tag_stack.pop()
        self.tag_stack.pop()

    def handle_data(self, data):
        """
        Handle raw text in the document (i.e. document body content)
        :param data: String of data
        :return: None
        """

        # Medium export files have a footer with junk that's not part of the original post.
        # Stop processing entirely if we hit the document footer.
        if self.seen_footer:
            return

        # If this text is part of an image caption, slap that caption on the last Image card so the caption
        # ends up in the right place and bail out.
        if "figcaption" in self.tag_stack:
            self.cards[-1][1]["caption"] = data
            return

        # If we are nested inside a <pre>, we are dealing with code content. Just append it to the current code
        # card and bail.
        if "pre" in self.tag_stack:
            self.cards[-1][1]["code"] += data
            return

        # If we got this fair, we have regular HTML text that may or may not be nested inside a <strong>, <em>, etc tag.
        # In Mobiledoc, the easiest way to to annotate each text string with all the formats (strong, em) etc that apply
        # to it.
        # So let's loop through the html tag stack and see all the formatting tags that apply to this piece of text.
        markups_for_data = []
        markup_count = 0

        body = []
        if "a" in self.tag_stack:
            markups_for_data.append(len(self.markups) - 1)
            markup_count += 1
        if "em" in self.tag_stack:
            markups_for_data.append(0)
            markup_count += 1
        if "strong" in self.tag_stack:
            markups_for_data.append(1)
            markup_count += 1

        # Finally, generate a Mobiledoc tag containing the text and all the formatting tags that apply to it.
        body = [0, markups_for_data, markup_count, data]

        self.current_markers.append(body)

    def convert(self):
        """
        Return a Mobiledoc version of a parsed HTML doc.
        Call this after calling .feed(html)
        :return:
        """
        return {
            "version": "0.3.1",
            "atoms": self.atoms,
            "cards": self.cards,
            "markups": self.markups,
            "sections": self.sections
        }



