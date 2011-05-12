import os
import sys

from optparse import OptionParser
from pantheon import backup
from pantheon import logger

# Set up logging.
log = logger.logging.getLogger("archiver")

def main():
    usage = "usage: %prog [options] PATH"
    parser = OptionParser(usage=usage, 
                          description="Archive a file to remote storage.")
    parser.add_option('-t', '--threshold', type="int", dest="threshold", default=4194304000, help='Filesize at which we switch to multipart upload.')
    parser.add_option('-c', '--chunksize', type="int", dest="chunksize", default=4194304000, help='The size to break multipart uploads into.')
    (options, args) = parser.parse_args()
    for arg in args:
        if os.path.isfile(arg):
            path = arg
            filename = os.path.basename(path)
            log.info('Moving archive to external storage.')
            try:
                backup.Archive(path, options.threshold, options.chunksize).submit()
            except:
                log.exception('Upload to remote storage unsuccessful.')
                raise
            else:
                log.info('Upload of %s to remote storage complete.' % 
                              filename)
        else:
            sys.exit('First arguement not a file path.')


if __name__ == '__main__':
    main()

