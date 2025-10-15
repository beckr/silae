# Silae downloader ⬇ 

Silae downloader is an automatic tool which replicates the remote Silae drive locally.

## Overview

```bash
usage: main.py [-h] [-d DESTINATION_FOLDER] [-i]

Script to download files from edocperso.fr

options:
  -h, --help            show this help message and exit
  -d DESTINATION_FOLDER, --destination-folder DESTINATION_FOLDER
                        Destination folder for downloaded files
  -i, --ignore-existing
                        Ignore existing files in the destination folder. Do not download theses files again.
```

## Quick start

> There is a docker packaged version as well below

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/beckr/silae.git
cd silae
```

2. Install dependencies with uv:
```bash
uv sync
```

3. Set up your environment variables:
```bash
# Copy the example environment file
cp secrets.env.tpl secrets.env

# Edit secrets.env and add your credentials
# LOGIN=your@email.com
# PASSWORD=yourPassword
```

4. Enable virtual env 

```bash
source .venv/bin/activate
```

4. Run

```bash
python src/silae/main.py -d /tmp
```


## Docker

1. Build the image
```bash
docker build -t silae:latest .
```

2. Run 
```bash
docker run --rm \
 -v /Users/me/downloads:/app/silae/downloads \
 -e DOWNLOAD_DIR=/app/silae/downloads \
 -e LOG_FILE_PATH=/app/silae/downloads/downloader.log \
 -e LOGIN=user@email.fr \
 -e PASSWORD=Password \
 silae:latest
```


 > Note: if your password contains a shell reserved word (like `$` or `!`), you must escape it like this 
`-e PASSWORD=Pas\$w0rd\! \`


[![better commits is enabled](https://img.shields.io/badge/better--commits-enabled?style=for-the-badge&logo=git&color=a6e3a1&logoColor=D9E0EE&labelColor=302D41)](https://github.com/Everduin94/better-commits)