import hashlib
import base64
import httplib
import sys
import os
import logging
import json
import pprint

# Set up logging.
logger = logging.getLogger("Archiver")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

CERTIFICATE = "/etc/pantheon/system.pem"
API_SERVER = "api.getpantheon.com"
ARCHIVE_SERVER = "s3.amazonaws.com"

path = sys.argv[1]
filename = os.path.basename(path)

connection = httplib.HTTPSConnection(
    API_SERVER,
    8443,
    key_file = CERTIFICATE,
    cert_file = CERTIFICATE
)

def hash_file(path):
    hash = hashlib.md5()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(128*hash.block_size), ''):
            hash.update(chunk)
    return base64.b64encode(hash.digest())

# Get the MD5 hash of the file.
logger.debug("Archiving file at path: %s" % path)
hash = hash_file(path)
logger.debug("Hash of file is: %s" % hash)

# Get the authorization headers.
headers = {'Content-Type': 'application/x-tar',
           'Content-MD5': hash}
encoded_headers = json.dumps(headers)
connection.request("PUT", "/sites/self/archive/" + filename, encoded_headers)
complete_response = connection.getresponse()
if complete_response.status == 200:
    logger.debug('Successfully obtained authorization.')
else:
    logger.debug('Obtaining authorization failed.')
    exit(1)
#complete_response.reason
encoded_info = complete_response.read()
info = json.loads(encoded_info)

# Transfer the file to long-term storage.
file = open(path)
arch_connection = httplib.HTTPSConnection(ARCHIVE_SERVER)
arch_connection.request("PUT", info['path'], file, info['headers'])
arch_complete_response = arch_connection.getresponse()
if arch_complete_response.status == 200:
    logger.debug('Successfully pushed the file to the archive.')
else:
    logger.debug('Uploading the file to the archive failed.')
    exit(2)

# Notify the event system of the completed transfer.
connection.request("PUT", "/sites/self/archive/" + filename + "/complete")
