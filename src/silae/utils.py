import re
import os
from typing import Dict, List, Union


def to_snake_case(s: str) -> str:
    """Convert a string from camelCase or PascalCase to snake_case.

    Args:
        s: The input string to convert.

    Returns:
        The converted string in snake_case.
    """
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    s = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower()


def convert_keys_to_snake_case(data: Union[Dict, List]) -> Union[Dict, List]:
    """Recursively convert all dictionary keys in a nested structure to snake_case.

    Args:
        data: The input data structure which can be a dictionary, list, or other type.

    Returns:
        The input data structure with all dictionary keys converted to snake_case.
        Non-dictionary and non-list items are returned unchanged.
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = to_snake_case(key)
            new_dict[new_key] = convert_keys_to_snake_case(value)
        return new_dict
    elif isinstance(data, list):
        return [convert_keys_to_snake_case(item) for item in data]
    else:
        return data


def clean_filename(filename: str):
    """
    Cleans a filename to be OS-safe using built-in functions.

    Args:
        filename (str): The filename to be cleaned.

    Returns:
        str: The cleaned filename.
    """
    # Normalize the path
    filename = os.path.normpath(filename)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Remove special characters using a list comprehension
    filename = ''.join(c for c in filename if c.isalnum()
                       or c in ('-', '_', '.'))

    # Remove consecutive underscores
    while '__' in filename:
        filename = filename.replace('__', '_')

    # Remove leading and trailing underscores
    filename = filename.strip('_')

    return filename
