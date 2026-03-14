import argparse
import os
import logging
from typing import Optional

import requests
from dotenv import load_dotenv

from models import Context, File
from utils import clean_filename

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

rotating_handler = RotatingFileHandler(
    os.getenv('LOG_FILE_PATH', 'edocperso_downloader.log'),
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=5,
    encoding='utf-8'
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        rotating_handler,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

URL_POST_AUTHENTICATION = 'https://edocperso.fr/edp-back/api/v1/login'
URL_GET_FOLDERS = 'https://edocperso.fr/edp-back/api/v1/folders'
URL_POST_DOCUMENTS = 'https://edocperso.fr/edp-back/api/v1/documents'
URL_POST_DOWNLOAD = 'https://edocperso.fr/edp-back/api/v1/documents/download'


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
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {context.token}"
    }

    logger.debug(f"download_document headers={headers}")

    data = {
        "documentIds": [f"{file.id}"],
        "folderIds": []
    }

    logger.debug(f"download_document data={data}")

    try:
        filename = clean_filename(file.name)
        filepath = os.path.join(folder_path, f"{filename}{file.extension}")

        if ignore_existing and os.path.exists(filepath):
            logger.info(f"Ignore existing file {filepath}")
            return filepath

        response = requests.post(URL_POST_DOWNLOAD, headers=headers,
                                 json=data, cookies=context.cookies)
        response.raise_for_status()  # Raise an error for bad status codes

        with open(filepath, 'wb') as f:
            f.write(response.content)

        logger.info(f"Document saved to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return None


def main(destination_folder: str, ignore_existing: bool = False):
    """
    Main function to authenticate and download documents from edocperso.fr.

    Args:
        destination_folder: Path to the folder where files should be saved
        ignore_existing: If True, skip downloading files that already exist
    """
    logger.info("-"*80)
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
        'Content-Type': 'application/json',
    }

    data = {
        'email': login,
        'password': password
    }

    # Authenticate
    response = requests.post(URL_POST_AUTHENTICATION,
                             headers=headers, json=data)
    response.raise_for_status()

    response_data = response.json()

    token = "EMPTY"

    try:
        # Extract token
        token = response_data["token"]

        logger.info("Authenticated")

        logger.debug(f"Response for URL_AUTHENTICATION : {response_data}")
    except Exception as e:
        logger.error(f"Error extracting token: {e}")

    # Extract cookies from the response
    cookies = response.cookies

    # Request headers
    headers = {
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json;charset=utf-8',
        'Authorization': f"Bearer {token}"
    }

    # Get initial folder structure using new API
    folders_response = requests.get(
        URL_GET_FOLDERS, headers=headers, cookies=cookies)

    folders_response.raise_for_status()

    logger.info("Got folders list")

    folders_data = folders_response.json()

    logger.debug(f"Get folder response: {folders_data}")

    context = Context(token=token, cookies=cookies)

    # Build folder hierarchy from response
    folders_dict = {}
    if 'folders' in folders_data:
        for folder_info in folders_data['folders']:
            folders_dict[folder_info['id']] = folder_info

    # Find root folders (those with no parentId)
    root_folders = [f for f in folders_data.get(
        'folders', []) if f.get('parentId') is None]

    # Process all folders recursively starting from root folders
    for root_folder in root_folders:
        process_folder_recursive(
            context, destination_folder, headers, cookies,
            folders_dict, root_folder, ignore_existing)


def process_folder_recursive(
    context: Context,
    destination_folder: str,
    headers: dict,
    cookies,
    folders_dict: dict,
    folder_info: dict,
    ignore_existing: bool
) -> None:
    """
    Process a folder and its children recursively.

    Args:
        context: Authentication context
        destination_folder: Base folder path for downloads
        headers: HTTP headers for API requests
        cookies: Authentication cookies
        folders_dict: Dictionary of all folders by ID
        folder_info: Current folder information
        ignore_existing: If True, skip existing files
    """
    folder_id = folder_info.get('id')
    folder_name = folder_info.get('name', 'Unknown')
    logger.info(f"Processing folder: {folder_name} ({folder_id})")

    # Get documents for this folder
    documents_data = {
        'paging': {'limit': 1000, 'offset': 0},
        'folderId': folder_id
    }

    documents_response = requests.post(
        URL_POST_DOCUMENTS, headers=headers, json=documents_data, cookies=cookies)

    documents_response.raise_for_status()

    documents_json = documents_response.json()

    logger.debug(f"Get (POST) documents response: {documents_json}")

    # Create the folder on disk
    folder_path = os.path.join(destination_folder, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    if 'items' in documents_json:
        for doc in documents_json['items']:
            # Create File object from document
            file = File(
                id=doc.get('id'),
                name=doc.get('title'),
                folder_id=doc.get('folderId'),
                extension=doc.get('fileExtension')
            )
            logger.debug(f"Getting document {doc}")
            # Download the file
            download_document(context, folder_path, file, ignore_existing)

    # Process child folders recursively
    children_ids = folder_info.get('children', [])
    logger.debug(f"children_ids={children_ids}")
    for child_id in children_ids:
        logger.debug(f"child_id={child_id}")
        logger.debug(
            f"{child_id} in {folders_dict}? {child_id in folders_dict}")
        if child_id in folders_dict:
            child_folder = folders_dict[child_id]
            logger.debug(f"child_folder={child_id}")
            process_folder_recursive(
                context, folder_path, headers, cookies,
                folders_dict, child_folder, ignore_existing)


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
