import httplib
import os
from pprint import pprint

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

    def read(self, size=-1):
        """Read within the range.
        This method will limit the size read based on the range.
        """
        size = self.__len__()
        rslt = self.fo.read(size)
        self.realpos += len(rslt)
        return rslt
    
    def __len__(self):
        """Handles calculating the amount of data to read based on
        the range.
        """
        #return self._calc_read_size(self.chunk_size)
        return self.lastbyte - self.firstbyte 

    def _do_seek(self,offset):
        """Seek based on whether wrapped object supports seek().
        offset is relative to the current position (self.realpos).
        """
        assert offset >= 0
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
    for i in range(fsize/chunk_size):
        print("Part: {0}".format(i+1))
        rfo = RangeableFileObject(file(fpath), (byte, byte + chunk_size))
        yield rfo
        rfo.close()
        byte += chunk_size
        print(float(byte)/float(fsize)*100)
    else:
        print("Part: {0}".format(i+2))
        rfo = RangeableFileObject(file(fpath), (byte, fsize))
        yield rfo
        print(float(100))
        rfo.close()

filepath = 'test.txt'
chunksize = 873
connection = httplib.HTTPConnection(
    'www.postbin.org',
)

for chunk in fbuffer(filepath, chunksize):
    connection.connect()
    connection.request("POST", '/1jskuz1', chunk)
    complete_response = connection.getresponse()
    pprint(complete_response.read())
    connection.close()
#    print(chunk.read())

