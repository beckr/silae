import os


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
