import click
from pathlib import Path
from medium_to_ghost.medium_post_parser import convert_medium_post_to_ghost_json
import time
import json
from zipfile import ZipFile
import logging
import sys
import shutil

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('medium_to_ghost')


def create_ghost_import_zip():
    """
    Zip up exported content in ./exported_content folder. Writes out medium_export_for_ghost.zip to disk.
    :return: None
    """
    shutil.make_archive("medium_export_for_ghost", "zip", "exported_content", logger=logger)


def create_export_file(converted_posts):
    """
    Create a Ghost import json from a list of Ghost post documents.
    :param converted_posts: Ghost formatted python docs.
    :return: A Dict representation of a ghost export file you can dump to json.
    """
    return {
        "db": [
            {
                "meta": {
                    "exported_on": int(time.time()),
                    "version": "2.0.3"
                },
                "data": {
                    "posts": converted_posts
                }
            }
        ]
    }


def parse_posts(posts):
    """
    Parse a list of Medium HTML posts
    :param posts: List of medium posts as dict with filename: html_content
    :return: Ghost versions of those same posts
    """
    converted_posts = []

    for name, content in posts.items():
        converted_post = convert_medium_post_to_ghost_json(name, content)
        if converted_post is not None:
            converted_posts.append(converted_post)

    return converted_posts


def extract_utf8_file_from_zip(zip, filename):
    """
    Python's zip library returns bytes, not unicode strings. So we need to
    convert Medium posts into utf-8 manually before we parse them.
    :param zip: Medium export zip file
    :param filename: post export filename to pull out as utf-8
    :return: utf-8 string data for a file
    """
    with zip.open(filename) as file:
        data = file.read().decode('utf8')

    return data


def extract_posts_from_zip(medium_zip):
    """
    Extract all Medium posts from the Medium export Zip file as utf-8 strings
    :param medium_zip: zip file from Medium
    :return: list of posts as a dict with filename: data
    """
    posts = {}

    for filename in medium_zip.namelist():
        if filename.startswith("posts/"):
            data = extract_utf8_file_from_zip(medium_zip, filename)
            posts[filename] = data

    return posts

@click.command()
@click.argument('medium_export_zipfile')
def main(medium_export_zipfile):
    export_folder = Path("exported_content")
    if Path(medium_export_zipfile).exists():
        export_folder.mkdir(parents=True, exist_ok=True)

        with ZipFile(medium_export_zipfile) as medium_zip, open(export_folder / "medium_export_for_ghost.json", "w") as output:
            posts = extract_posts_from_zip(medium_zip)
            exported_posts = parse_posts(posts)
            export_data = create_export_file(exported_posts)
            json.dump(export_data, output, indent=2)

        # Put everything in a zip file for Ghost
        create_ghost_import_zip()
        logger.info(f"Successfully created medium_export_for_ghost.zip. Upload this file to a Ghost 2.0+ instance!")
    else:
        print(f"Unable to find {medium_export_zipfile}.")
        exit(1)


if __name__ == "__main__":
    main()
