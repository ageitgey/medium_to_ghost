import logging
import urllib.request
from urllib.error import HTTPError
from pathlib import Path


def download_image_with_local_cache(url: str, cache_folder: Path):
    """
    Download an image file locally if it doesn't already exist.
    :param url: Image url to download
    :param cache_folder: Where to cache the image
    :return: The local path of the image (either downloaded or previously cached)
    """
    # Ensure cache folder exists
    cache_folder.mkdir(parents=True, exist_ok=True)

    # Send a User Agent so Medium doesn't return 403
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'medium_to_ghost post exporter')]
    urllib.request.install_opener(opener)

    logging.info(f"Downloading {url} to {cache_folder}")

    filename = url.split("/")[-1]
    # Medium has stars (*) in image filenames but ghost doesn't like this
    filename = filename.replace("*", "-")

    local_destination = cache_folder / filename

    if local_destination.exists():
        logging.info(f"{local_destination} already exists. Using cached copy.")
    else:
        try:
            local_filename, headers = urllib.request.urlretrieve(url, local_destination)
        except HTTPError as e:
            logging.error(f"Download failed for {local_destination}. Error Message: {e.msg}")

    return local_destination

