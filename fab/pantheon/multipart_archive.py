import hashlib
import base64
import httplib
import sys
import os
import logging
import json
import pprint

class RangeableFileObject():
    """File object wrapper to enable raw range handling.
    This was implemented primarilary for handling range 
    specifications for file:// urls. This object effectively makes 
    a file object look like it consists only of a range of bytes in 
    the stream.
    """
    
    def __init__(self, fo, rangetup):
        """Create a RangeableFileObject.
        fo       -- a file like object. only the read() method need be 
                    supported but supporting an optimized seek() is 
                    preferable.
        rangetup -- a (firstbyte,lastbyte) tuple specifying the range
                    to work over.
        The file object provided is assumed to be at byte offset 0.
        """
        self.fo = fo
        (self.firstbyte, self.lastbyte) = range_tuple_normalize(rangetup)
        self.realpos = 0
        self._do_seek(self.firstbyte)
        
    def __getattr__(self, name):
        """This effectively allows us to wrap at the instance level.
        Any attribute not found in _this_ object will be searched for
        in self.fo.  This includes methods."""
        if hasattr(self.fo, name):
            return getattr(self.fo, name)
        raise AttributeError, name

    def tell(self):
        """Return the position within the range.
        This is different from fo.seek in that position 0 is the 
        first byte position of the range tuple. For example, if
        this object was created with a range tuple of (500,899),
        tell() will return 0 when at byte position 500 of the file.
        """
        return (self.realpos - self.firstbyte)
    
    def read(self, size=-1):
        """Read within the range.
        This method will limit the size read based on the range.
        """
        size = self._calc_read_size(size)
        rslt = self.fo.read(size)
        self.realpos += len(rslt)
        return rslt
    
    def _calc_read_size(self, size):
        """Handles calculating the amount of data to read based on
        the range.
        """
        if self.lastbyte:
            if size > -1:
                if ((self.realpos + size) >= self.lastbyte):
                    size = (self.lastbyte - self.realpos)
            else:
                size = (self.lastbyte - self.realpos)
        return size

    def _do_seek(self,offset):
        """Seek based on whether wrapped object supports seek().
        offset is relative to the current position (self.realpos).
        """
        assert offset >= 0
        if not hasattr(self.fo, 'seek'):
            self._poor_mans_seek(offset)
        else:
            self.fo.seek(self.realpos + offset)
        self.realpos+= offset

    def seek(self,offset,whence=0):
        """Seek within the byte range.
        Positioning is identical to that described under tell().
        """
        assert whence in (0, 1, 2)
        if whence == 0:   # absolute seek
            realoffset = self.firstbyte + offset
        elif whence == 1: # relative seek
            realoffset = self.realpos + offset
        elif whence == 2: # absolute from end of file
            # XXX: are we raising the right Error here?
            raise IOError('seek from end of file not supported.')
        
        # do not allow seek past lastbyte in range
        if self.lastbyte and (realoffset >= self.lastbyte):
            realoffset = self.lastbyte
        
        self._do_seek(realoffset - self.realpos)

    def _poor_mans_seek(self,offset):
        """Seek by calling the wrapped file objects read() method.
        This is used for file like objects that do not have native
        seek support. The wrapped objects read() method is called
        to manually seek to the desired position.
        offset -- read this number of bytes from the wrapped
                  file object.
        raise RangeError if we encounter EOF before reaching the 
        specified offset.
        """
        pos = 0
        bufsize = 1024
        while pos < offset:
            if (pos + bufsize) > offset:
                bufsize = offset - pos
            buf = self.fo.read(bufsize)
            if len(buf) != bufsize:
                raise RangeError(9, 'Requested Range Not Satisfiable')
            pos+= bufsize
        
def range_tuple_normalize(range_tup):
    """Normalize a (first_byte,last_byte) range tuple.
    Return a tuple whose first element is guaranteed to be an int
    and whose second element will be '' (meaning: the last byte) or 
    an int. Finally, return None if the normalized tuple == (0,'')
    as that is equivelant to retrieving the entire file.
    """
    if range_tup is None: return None
    # handle first byte
    fb = range_tup[0]
    if fb in (None,''): fb = 0
    else: fb = int(fb)
    # handle last byte
    try: lb = range_tup[1]
    except IndexError: lb = ''
    else:  
        if lb is None: lb = ''
        elif lb != '': lb = int(lb)
    # check if range is over the entire file
    if (fb,lb) == (0,''): return None
    # check that the range is valid
    if lb < fb: raise RangeError(9, 'Invalid byte range: %s-%s' % (fb,lb))
    return (fb,lb)

def fbuffer(fpath, chunk_size):
    fsize = os.path.getsize(fpath)
    byte = 0
    for i in range(fsize/chunk_size + 1):
        fo = RangeableFileObject(file(fpath), (byte, byte + chunk_size))
        yield fo
        fo.close()
        byte += chunk_size
        print(((i+1) / float(fsize/chunk_size + 1))*100)

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
hash = hash_file(path)

# Get the authorization headers.
headers = {'Content-Type': 'application/x-tar',
           'Content-MD5': hash}
encoded_headers = json.dumps(headers)

connection.request("PUT", '{0}?uploads'.format(filename), headers)
print(conntect.response())
#for chunk in fbuffer('logging.conf', 234):
#    connection.request("PUT", '/%s?partNumber=%s&uploadId=%s' % (filename, part, upid), chunk, 'authheaders')
