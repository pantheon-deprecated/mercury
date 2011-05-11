import hashlib
import base64
import httplib
import sys
import os
import logging
import json
import rangeable_file

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

connection = httplib.HTTPSConnection(
    API_SERVER,
    8443,
    key_file = CERTIFICATE,
    cert_file = CERTIFICATE
)

def main(path):
    #filename = os.path.basename(path)
    #upid = initiate_multipart_archive(filename)
    #partno = 1
    #parts = []
    mpa = Multipart_archive(path)
    for chunk in rangeable_file.fbuffer(path, 2500):
        partno = mpa.partno
        mph = mpa.get_multipart_upload_header(chunk)
        chunk.seek(0)
        # Transfer the file to long-term storage.
        arch_connection = httplib.HTTPSConnection(mph['hostname'])
        arch_connection.request("PUT", mph['path'], chunk, mph['headers'])
        arch_complete_response = arch_connection.getresponse()
        if arch_complete_response.status == 200:
            logger.debug('Successfully pushed the file to the archive.')
        else:
            logger.debug('Uploading the file to the archive failed.')
            exit(2)
        etag = arch_complete_response.getheader('etag')
        mpa.parts.append((partno, etag))

    mpa.complete_multipart_upload()

class Multipart_archive:
    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.upid = self.initiate_multipart_archive(self.filename)
        self.partno = 1
        self.parts = []

    def hash_file(self, part):
        """ Return MD5 hash of part

        Keyword arguements:
        part -- the file object to hash

        """
        part_hash = hashlib.md5()
        for chunk in iter(lambda: part.read(128*part_hash.block_size), ''):
            part_hash.update(chunk)
        return base64.b64encode(part_hash.digest())


    def initiate_multipart_archive(self, filename):
        """ Return the upload id from ygg.

        Keyword arguements:
        filename -- the name of the file being imported

        """
        # Get the authorization headers.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'initiate'}
        encoded_headers = json.dumps(headers)
        connection.request("PUT", "/sites/self/archive/{0}".format(filename), 
                           encoded_headers)
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
        logger.debug('Return upload id.')
        return info

    def get_multipart_upload_header(self, part):
        """ Return the multipart upload headers from ygg.

        Keyword arguements:
        part -- file object of current chunk
        partno -- part number
        upid -- unique upload id

        """
        # Get the MD5 hash of the file.
        logger.debug("Archiving file at path: %s" % self.path)
        part_hash = self.hash_file(part)
        logger.debug("Hash of file is: %s" % part_hash)
        connection.connect()
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash,
                   'multipart': 'upload',
                   'upload-id': self.upid,
                   'part-number': self.partno}
        encoded_headers = json.dumps(headers)
        connection.request("PUT", "/sites/self/archive/{0}".format(self.filename), encoded_headers)
        complete_response = connection.getresponse()
        if complete_response.status == 200:
            logger.debug('Successfully obtained authorization.')
        else:
            logger.debug('Obtaining authorization failed.')
            exit(1)
        #complete_response.reason
        encoded_info = complete_response.read()
        #connection.close()
        self.partno+=1
        return json.loads(encoded_info)

    def complete_multipart_upload(self):
        # Notify the event system of the completed transfer.
        connection.connect()
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'complete',
                   'upload-id': self.upid,
                   'parts': self.parts}
        encoded_headers = json.dumps(headers)
        connection.request("PUT", "/sites/self/archive/{0}".format(self.filename), 
                           encoded_headers)
        complete_response = connection.getresponse()
        if complete_response.status == 200:
            logger.debug('Successfully obtained authorization.')
        else:
            logger.debug('Obtaining authorization failed.')
            exit(1)
        #complete_response.reason
        encoded_info = complete_response.read()
        return encoded_info

if __name__ == '__main__':
    main(sys.argv[1])
#connection.request("PUT", "/sites/self/archive/{0}/complete".format(filename))

