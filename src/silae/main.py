import argparse
import os
import logging
from typing import List, Optional

import requests
from dotenv import load_dotenv

from models import Context, File, Folder, Response
from utils import clean_filename, convert_keys_to_snake_case

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

rotating_handler = RotatingFileHandler(
    os.getenv('LOG_FILE_PATH', 'edocperso_downloader.log'),
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=5,
    encoding='utf-8'
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        rotating_handler,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

URL_GET_CONTENT = "https://v2-app.edocperso.fr/edocPerso/V1/edpDoc/getContent"
URL_AUTHENTICATION = 'https://edocperso.fr/index.php?api=Authenticate&a=doAuthentication'
URL_GET_FOLDERS_AND_FILES = "https://v2-app.edocperso.fr/edocPerso/V1/edpUser/getFoldersAndFiles"


def map_json_to_classes(json_data: str) -> List[Folder]:
    """
    Convert JSON data to Folder objects.

    Args:
        json_data: JSON string containing folder and file information

    Returns:
        List of Folder objects if successful, empty list otherwise
    """
    json_data = convert_keys_to_snake_case(json_data)
    if json_data["status"] == "success":
        response = Response.from_dict(json_data)
        return response.content
    else:
        logger.error(f"Error of API response: {json_data['status']}")
        return []

def download_document(context: Context, folder_path: str, file: File, ignore_existing: bool) -> Optional[str]:
    """
    Download a document from edocperso.fr and save it to the specified folder.

    Args:
        context: Authentication context containing token and cookies
        folder_path: Path to the folder where the file should be saved
        file: File object containing document information
        ignore_existing: If True, skip download if file already exists

    Returns:
        Path to the downloaded file if successful, None otherwise

    Raises:
        OSError: If the destination folder doesn't exist
    """
    if not os.path.exists(folder_path):
        raise OSError(
            f"Folder has not been created {folder_path} for file {file.name}")

    headers = {
        'Accept': 'application/octet-stream',
        'Content-Type': 'application/json;charset=utf-8'
    }
    data = {
        "sessionId": context.token,
        "documentId": file.id
    }

    try:
        filename = clean_filename(file.name)
        filepath = os.path.join(folder_path, f"{filename}.{file.extension}")

        if ignore_existing and os.path.exists(filepath):
            logger.info(f"Ignore existing file {filepath}")
            return filepath

        response = requests.post(URL_GET_CONTENT, headers=headers,
                                 json=data, cookies=context.cookies)
        response.raise_for_status()  # Raise an error for bad status codes

        with open(filepath, 'wb') as f:
            f.write(response.content)

        logger.info(f"Document saved to {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading document: {e}")
        return None

def main(destination_folder: str, ignore_existing: bool = False):
    """
    Main function to authenticate and download documents from edocperso.fr.

    Args:
        destination_folder: Path to the folder where files should be saved
        ignore_existing: If True, skip downloading files that already exist
    """
    # Load secrets from .env file
    load_dotenv('secrets.env')

    login = os.getenv('LOGIN')
    password = os.getenv('PASSWORD')

    if not login or not password:
        logger.error("LOGIN and PASSWORD environment variables must be set")
        exit(1)

    logger.info(f"Gathering documents for {login}")

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json;charset=utf-8',
    }

    data = {
        'login': login,
        'password': password
    }

    # Authenticate
    response = requests.post(URL_AUTHENTICATION, headers=headers, json=data)
    response.raise_for_status()

    response_data = response.json()

    if response_data["status"] == "error":
        logger.error(
            f"Error in response: {response_data["content"]}", response)
        exit(1)

    logger.info("Authenticated")

    logger.debug(f"Response for URL_AUTHENTICATION : {response_data}")

    # Extract login url
    login_url = response_data['content']['loginUrl']
    logger.debug(f"URL de connexion: {login_url}")

    # Extract JWT token from login URL
    token = login_url.split('/')[-1]
    logger.debug(f"Token JWT: {token}")

    # Extract cookies from the response
    cookies = response.cookies

    # Get on login (server state)
    login_response = requests.get(login_url, cookies=cookies)

    login_response.raise_for_status()

    logger.debug("Login ok")

    # En-têtes de la requête
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json;charset=utf-8',
    }

    # Données de la requête
    data = {
        'sessionId': token
    }

    context = Context(token=token, cookies=cookies)

    # Get the folder and files list
    folders_files_response = requests.post(
        URL_GET_FOLDERS_AND_FILES, headers=headers, json=data, cookies=cookies)

    folders_files_response.raise_for_status()

    logger.info("Got files list")

    mapped_data = map_json_to_classes(
        folders_files_response.json())

    logger.debug("Gathered files and folders %s", mapped_data)

    for content in mapped_data:
        getOrCreateFolderStructure(
            context, destination_folder, content, ignore_existing)

def getOrCreateFolderStructure(context: Context, destination_folder: str, content: Folder, ignore_existing: bool = False) -> None:
    """
    Process a folder structure and create/download its contents.

    Args:
        context: Authentication context
        destination_folder: Base folder path for downloads
        content: Folder object to process
        ignore_existing: If True, skip existing files
    """
    if content is not None:
        getOrCreateFolder(context, destination_folder,
                          content, ignore_existing)
    else:
        logger.warning("No content")

def getOrCreateFolder(context: Context, destination_folder: str, folder: Folder, ignore_existing: bool) -> None:
    """
    Create a folder and process its contents recursively.

    Args:
        context: Authentication context
        destination_folder: Parent folder path
        folder: Folder object to process
        ignore_existing: If True, skip existing files
    """
    folder_path = os.path.join(destination_folder, folder.name)
    logger.info(f"Creating or getting {folder_path}")
    os.makedirs(folder_path, exist_ok=True)
    for child in folder.children:
        if child.type == "folder":
            getOrCreateFolder(context, folder_path, child, ignore_existing)
        elif child.type == "file":
            logger.info(f"Downloading file {child.name}")
            try:
                download_document(context, folder_path, child, ignore_existing)
            except requests.exceptions.HTTPError as e:
                logger.error(f"Error downloading {child.name}")
                logger.error(e)
            except OSError as e:
                logger.error(f"Error folder not created {folder_path} ")
                logger.error(e)
        else:
            logger.warning(f"Unknown type {child.type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Script to download files from edocperso.fr')
    parser.add_argument('-d', '--destination-folder', type=str,
                        help='Destination folder for downloaded files')
    parser.add_argument('-i', '--ignore-existing', action='store_true',
                        help='Ignore existing files in the destination folder. Do not download theses files again.')
    args = parser.parse_args()
    if args.destination_folder is None:
        print("⨯ No destination folder provided. Use see -h for help")
        exit(1)
    main(args.destination_folder, args.ignore_existing)
