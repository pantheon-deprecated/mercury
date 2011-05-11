import os

class RangeableFileObject():
    """File object wrapper to enable raw range handling.

    This object effectively makes a file object look like it consists only 
    of a range of bytes in the stream.

    """
    
    def __init__(self, fo, rangetup):
        """Create a RangeableFileObject.

        fo       -- a file like object.
        rangetup -- a (firstbyte,lastbyte) tuple specifying the range to 
                    work over.
        The file object provided is assumed to be at byte offset 0.

        """
        self.fo = fo
        (self.firstbyte, self.lastbyte) = range_tuple_normalize(rangetup)
        self.realpos = 0
        self._do_seek(self.firstbyte)
        
    def __getattr__(self, name):
        """Any attribute not found in _this_ object will be searched for
        in self.fo.

        name -- name of attribute to search for.
        This includes methods.

        """
        if hasattr(self.fo, name):
            return getattr(self.fo, name)
        raise AttributeError, name

    def read(self, size=None):
        """Read and return within the range.

        size -- the size of the provided range
        This method will limit the size read based on the range.

        """
        size = self._read_size(size) if size else \
               self._read_size(self.__len__())
        rslt = self.fo.read(size)
        self.realpos += len(rslt)
        return rslt

    def _read_size(self, size):
        """Return actual size to be read

        size -- Length of the current range
        Handles calculating the amount of data to read based on the range.

        """
        if self.lastbyte:
            if size > -1:
                if ((self.realpos + size) >= self.lastbyte):
                    size = (self.lastbyte - self.realpos)
            else:
                size = (self.lastbyte - self.realpos)
        return size

    def __len__(self):
        """Returns the length of the given range in bytes"""
        return self.lastbyte - self.firstbyte 

    def _do_seek(self,offset):
        """Seek based on whether wrapped object supports seek().
        offset -- is relative to the current position (self.realpos).
        """
        assert (self.realpos + offset) >= 0
        self.fo.seek(self.realpos + offset)
        self.realpos+= offset

    def seek(self,offset,whence=0):
        """Seek within the byte range.

        offset -- The byte to seek to
        whence -- Switch between relative and absolute seeking (default 0)
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
    """ Yield rangeable file object

    Keyword arguements:
    fpath      -- path to the file
    chunk_size -- size of the chunk to buffer
    Generator that yields a rangeable file object of a given chunk_size

    """
    fsize = os.path.getsize(fpath)
    byte = 0
    for i in range(fsize/chunk_size):
        if (fsize > chunk_size):
            rfo = RangeableFileObject(file(fpath), (byte, byte + chunk_size))
            yield rfo
            rfo.close()
            byte += chunk_size
    else:
        rfo = RangeableFileObject(file(fpath), (byte, fsize))
        yield rfo
        rfo.close()

""" Test code
import httplib
import sys
filepath = sys.argv[1]
chunksize = 804
connection = httplib.HTTPConnection(
    'www.postbin.org',
)

for chunk in fbuffer(filepath, chunksize):
    connection.connect()
    connection.request("POST", '/1jskuz1', chunk)
    complete_response = connection.getresponse()
    connection.close()
#    print(chunk.read())
"""

