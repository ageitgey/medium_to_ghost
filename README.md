# Medium to Ghost 2.0

Feeling locked into Medium.com? Instantly move all your content (formatted posts + images) to an open source blog!

![Migrate your data out of Medium to Ghost](https://user-images.githubusercontent.com/896692/44764117-0c097c80-ab03-11e8-8925-bcc4c584059c.png)

This code converts all your Medium.com posts to a Ghost 2.0.x import file. With that,
you can import all your content into a Ghost blog (hosted anywhere) in seconds. Your posts keep
the same formatting and all your images are migrated over too.

## Why?

Medium.com is a nice platform for creating blog posts. I use it and enjoy it.

But you should never feel like your content is locked into someone else's privately-owned platform. This 
gives you the option to move your content to your own blog if you want to do it. It's also a quick way 
to back up all your Medium.com content (especially your images which they don't export) in case the site disappears 
someday.

I hacked this together quickly to move my blog, [Machine Learning is Fun!](https://www.machinelearningisfun.com/) from 
Medium to a self-hosted Ghost site. Hopefully it's useful to someone else too. More options is always good, right? 

## Requirements

- A blog running Ghost v2.0.3+ (*NOT Ghost 1.x*). Both Self-hosted or professionally hosted Ghost instances are both 
  fine.
- A Medium.com account where you've previously written content. 
- Python 3.6+ to run this program

## Installing this program

After you've [installed Python 3.6+](https://www.python.org/downloads/), you can install this program by opening up a 
terminal window and running this command:

### Mac / Linux

```python
pip3 install medium_to_ghost
```

### Windows

```python
pip install medium_to_ghost
```

## How to use this to export your Medium content

1. Install [Python 3.6+](https://www.python.org/downloads/). Lower versions won't work!
1. Install this program (See "Installing this program")
1. Go to https://medium.com/me/settings and find `Download your information`. There's a button to export your data and 
   email it to you. 
1. Wait for the email from Medium and download your zip file. This will give you a file called `medium-export.zip`
1. Run `python3 medium_to_ghost.py medium-export.zip` which will produce `medium_export_for_ghost.zip`.
   This new zip file contains all your converted Medium posts and images from your posts. Make sure to put the full path
   to the zip file if it's not in the current directory. This may take a few minutes if you have lots of images
   in your posts since they all have to be downloaded.
1. Go into Ghost 2.0.3+, navigate to /ghost/, click on 'Labs', and choose to import that zip file.
1. That's it!

## What gets moved over

When exporting content from Medium, the following features are supported:

- Both published articles and drafts are moved over. So even if you are in the middle of writing a new
  post, it should be a seamless transition.
- Most Medium.com content is replicated perfectly in Ghost, including text formatting, embedded Github gists, image
  cards with captions, Upscribe mailing list signup forms, etc.
- If your Medium posts have a featured image, that will come over automatically too.

## What is lost when moving over

- Comments are not moved over to Ghost
- Story highlights are not moved over to Ghost
- I tried to make the Ghost output as similar to Medium as possible. However, there may be bugs or types of 
  Medium content I haven't seen before, so always check the results in Ghost carefully. I just made sure it worked
  for all my articles. No warranty! :)

## Warnings!

- Hopefully this code will work for you, but it have bugs and cause your computer to explode. Make sure you 
  test everything out on a test Ghost instance before you import anything into a live blog.
- Ghost does not let you set a Canonical Url for a post! This means that your new Ghost blog will
  duplicate your existing Medium.com posts and that may mess with your Google rankings. Please [vote for
  this suggestion on Ghost](https://forum.ghost.org/t/change-canonical-url/28) and ask them nicely to 
  support the ability to set canonical urls. If that was supported, this tool could automatically set 
  up the exported Ghost posts to point back to Medium URLs to avoid any SEO impact.
- Ghost 2.0.3 has [a bug with image paths in import files](https://github.com/TryGhost/Ghost/issues/9821).
  This tool may need to be updated when that bug is fixed in order for it to keep working, but it works 
  for now with 2.0.3. 