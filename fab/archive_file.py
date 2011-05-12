import hashlib
import base64
import httplib
import sys
import os
import logging
import json

from pantheon import backup

# Set up logging.
logger = logging.getLogger("Archiver")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

#TODO: Add optional cli arguements to set threshold and chunksize
def main():
    if os.path.isfile(sys.argv[1]):
        arch = backup.Archive(sys.argv[1])
        arch.submit()
    else:
        print('First arguement not a file.')

if __name__ == '__main__':
    main()

