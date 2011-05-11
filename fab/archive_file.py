import hashlib
import base64
import httplib
import sys
import os
import logging
import json

from pantheon import rangeable_file

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

#TODO: Add optional cli arguements to set threshold and chunksize
def main():
    if os.path.isfile(sys.argv[1]):
        archive = Archive(sys.argv[1])
        archive.submit()
    else:
        print('First arguement not a file.')

class Archive:
    def __init__(self, path, threshold=4194304000, chunk_size=4194304000):
        self.connection = httplib.HTTPSConnection(
                                                  API_SERVER,
                                                  8443,
                                                  key_file = CERTIFICATE,
                                                  cert_file = CERTIFICATE)
        self.path = path
        self.filesize = os.path.getsize(path)
        self.threshold = threshold
        self.filename = os.path.basename(path)
        self.partno = 0
        self.parts = []
        self.chunk_size = chunk_size

    def is_multipart(self):
        # Amazon S3 has a minimum upload size of 5242880
        assert self.filesize >= 5242880,"File size is too small."
        # Amazon S3 has a minimum upload size of 5242880
        assert self.chunk_size >= 5242880,"Chunk size is too small."
        return True if self.filesize > self.threshold else False

    def submit(self):
        if self.filesize < self.threshold:
            # Amazon S3 has a maximum upload size of 5242880000
            assert self.threshold < 5242880000,"Threshold is too large."
            fo = open(self.path)
            info = json.loads(self.get_upload_header(fo))
            fo.seek(0)
            response = self._arch_request(fo, info)
            self.complete_upload()
        elif self.is_multipart():
            self.upid = json.loads(self.initiate_multipart_upload())
            for chunk in rangeable_file.fbuffer(self.path, self.chunk_size):
                info = json.loads(self.get_multipart_upload_header(chunk))
                chunk.seek(0)
                response = self._arch_request(chunk, info)
                etag = response.getheader('etag')
                self.parts.append((self.partno, etag))
            self.complete_multipart_upload()
        self.connection.close()

    def hash_file(self, fo):
        """ Return MD5 hash of file object

        Keyword arguements:
        fo -- the file object to hash

        """
        fo_hash = hashlib.md5()
        for chunk in iter(lambda: fo.read(128*fo_hash.block_size), ''):
            fo_hash.update(chunk)
        return base64.b64encode(fo_hash.digest())

    def initiate_multipart_upload(self):
        """ Return the upload id from api."""
        # Get the authorization headers.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'initiate'}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def get_multipart_upload_header(self, part):
        """ Return multipart upload headers from api.

        Keyword arguements:
        part -- file object to get headers for

        """
        # Get the MD5 hash of the file.
        logger.debug("Archiving file at path: %s" % self.path)
        part_hash = self.hash_file(part)
        logger.debug("Hash of file is: %s" % part_hash)
        self.partno+=1
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash,
                   'multipart': 'upload',
                   'upload-id': self.upid,
                   'part-number': self.partno}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def get_upload_header(self, fo):
        """ Return upload headers from api.

        Keyword arguements:
        fo -- file object to get headers for

        """
        logger.debug("Archiving file at path: %s" % self.path)
        part_hash = self.hash_file(fo)
        logger.debug("Hash of file is: %s" % part_hash)
        headers = {'Content-Type': 'application/x-tar',
                   'Content-MD5': part_hash}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    #TODO: re-work multipart upload completion into the rest api
    def complete_multipart_upload(self):
        """ Return multipart upload completion response from api."""
        # Notify the event system of the completed transfer.
        headers = {'Content-Type': 'application/x-tar',
                   'multipart': 'complete',
                   'upload-id': self.upid,
                   'parts': self.parts}
        encoded_headers = json.dumps(headers)
        path = "/sites/self/archive/{0}".format(self.filename)
        return self._api_request(path, encoded_headers)

    def complete_upload(self):
        """ Return upload completion response from api."""
        path = "/sites/self/archive/{0}/complete".format(self.filename)
        return self._api_request(path)

    def _api_request(self, path, encoded_headers=None):
        """Returns encoded response data from api.

        Keyword arguements:
        path            -- api request path
        encoded_headers -- api request headers
        Make PUT request to config server.

        """
        self.connection.connect()
        if encoded_headers:
            self.connection.request("PUT", path, encoded_headers)
        else:
            self.connection.request("PUT", path)

        complete_response = self.connection.getresponse()
        if complete_response.status == 200:
            logger.debug('Successfully obtained authorization.')
        else:
            logger.debug('Obtaining authorization failed.')
            exit(1)
        encoded_info = complete_response.read()
        return encoded_info

    def _arch_request(self, data, info):
        """Returns encoded response data from archive server.

        Keyword arguements:
        data -- data to archive
        info -- api request headers
        Make PUT request to store data on archive server.

        """
        # Transfer the file to long-term storage.
        arch_connection = httplib.HTTPSConnection(info['hostname'])
        arch_connection.request("PUT", 
                                info['path'], 
                                data, 
                                info['headers'])
        arch_complete_response = arch_connection.getresponse()
        if arch_complete_response.status == 200:
            logger.debug('Successfully pushed the file to the archive.')
        else:
            logger.debug('Uploading the file to the archive failed.')
            exit(2)
        return arch_complete_response

if __name__ == '__main__':
    main()

