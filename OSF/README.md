# OSF uploading

## Installation
Install the OSF command line interface from [GitHub](https://github.com/osfclient/osfclient).
You can install from PyPI, but this version is not as good as the GitHub version, at least at time of writing.

```
git clone https://github.com/osfclient/osfclient
cd osfclient
python -m pip install .
```

## Usage
Change `.osfcli.config` and update the `if __name__ == "__main__"` block  in `osf_upload_folder.py` with details of your OSF login. Make sure not to commit these changes to any online repositories!  
Currently `osf_upload_folder.py` does not provide any command line interface, so you will have to directly update the main control code to upload the desired folders.
