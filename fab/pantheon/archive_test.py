import hashlib
import base64
import httplib
import sys
import os
import logging
import json
import multipart_archive
from pprint import pprint

# Set up logging.
logger = logging.getLogger("Archiver")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

CERTIFICATE = "/etc/pantheon/system.pem"
API_SERVER = "184.106.214.232"
ARCHIVE_SERVER = "s3.amazonaws.com"

path = sys.argv[1]
filename = os.path.basename(path)

connection = httplib.HTTPSConnection(
    API_SERVER,
    8443,
    key_file = CERTIFICATE,
    cert_file = CERTIFICATE
)

def hash_file(part):
    """ part: file object to generate a MD5 hash from
    """
    part_hash = hashlib.md5()
    for chunk in iter(lambda: part.read(128*part_hash.block_size), ''):
        part_hash.update(chunk)
    return base64.b64encode(part_hash.digest())


def initiate_multipart_archive(filename):
    """ Returns upload id for multipart upload
    """
    # Get the authorization headers.
    headers = {'Content-Type': 'application/x-tar',
               'multipart': 'initiate'}
    encoded_headers = json.dumps(headers)
    connection.request("PUT", "/sites/self/archive/{0}".format(filename), encoded_headers)
    complete_response = connection.getresponse()
    if complete_response.status == 200:
        logger.debug('Successfully obtained authorization.')
    else:
        logger.debug('Obtaining authorization failed.')
        exit(1)
    #complete_response.reason
    encoded_info = complete_response.read()
    info = json.loads(encoded_info)
    connection.close()
    return info

upid = initiate_multipart_archive(filename)

print("\nInitiate Complete\n")
def get_multipart_upload_header(part, partno, upid):
    # Get the MD5 hash of the file.
    logger.debug("Archiving file at path: %s" % path)
    part_hash = hash_file(part)
    logger.debug("Hash of file is: %s" % part_hash)
    connection.connect()
    headers = {'Content-Type': 'application/x-tar',
               'Content-MD5': part_hash,
               'multipart': 'upload',
               'upload-id': upid,
               'part-number': partno}
    encoded_headers = json.dumps(headers)
    connection.request("PUT", "/sites/self/archive/{0}".format(filename), encoded_headers)
    complete_response = connection.getresponse()
    if complete_response.status == 200:
        logger.debug('Successfully obtained authorization.')
    else:
        logger.debug('Obtaining authorization failed.')
        exit(1)
    #complete_response.reason
    encoded_info = complete_response.read()
#    connection.close()
    return json.loads(encoded_info)

partno = 1
parts = []
for chunk in multipart_archive.fbuffer(path, 9000):
    mph = get_multipart_upload_header(chunk, partno, upid)
    pprint(mph)
    # Transfer the file to long-term storage.
    arch_connection = httplib.HTTPSConnection(mph['hostname'])
    arch_connection.request("PUT", mph['path'], chunk, mph['headers'])
    arch_complete_response = arch_connection.getresponse()
    if arch_complete_response.status == 200:
        logger.debug('Successfully pushed the file to the archive.')
        pprint(arch_complete_response.__dict__)
    else:
        logger.debug('Uploading the file to the archive failed.')
        pprint(arch_complete_response.__dict__)
        exit(2)
    etag = arch_complete_response.getheader('etag')
    parts.append((partno, etag))
    partno+=1

pprint(parts)

def complete_multipart_upload(upid, parts):
    # Notify the event system of the completed transfer.
    connection.connect()
    headers = {'Content-Type': 'application/x-tar',
               'multipart': 'complete',
               'upload-id': upid,
               'parts': parts}
    encoded_headers = json.dumps(headers)
    connection.request("PUT", "/sites/self/archive/{0}".format(filename), encoded_headers)
    complete_response = connection.getresponse()
    if complete_response.status == 200:
        logger.debug('Successfully obtained authorization.')
        print(complete_response.__dict__)
    else:
        logger.debug('Obtaining authorization failed.')
        print(complete_response.__dict__)
        exit(1)
    #complete_response.reason
    encoded_info = complete_response.read()
    pprint(encoded_info)

complete_multipart_upload(upid, parts)

#connection.request("PUT", "/sites/self/archive/{0}/complete".format(filename))

