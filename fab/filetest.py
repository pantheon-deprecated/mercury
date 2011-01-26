import os
import random
import shutil
import string
import tempfile
import unittest

from pantheon import onramp
from fabric.api import settings, hide

class FilePathTestCase(unittest.TestCase):
    """Test the import process of normalizing Drupal file paths.

    """

    def setUp(self):
        """Create a fake Drupal root and ImportTools object.

        """
        self.working_dir = tempfile.mkdtemp()
        self.test_import = self.TestImportTools(self.working_dir)

    def test_directory_defaultpath_defaultname(self):
        """sites/default/files."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/default/files',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist)

    def test_directory_defaultpath_othername(self):
        """sites/default/other."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/default/other',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_otherpath_defaultname(self):
        """sites/other/files."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/other/files',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_otherpath_othertname(self):
        """sites/other/other."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/other/other',
                                          exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_rootpath(self):
        """files."""
        start_path, final_path = self.setup_environment(files_dir='files',
                                                        exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        self.assertTrue(dir_exists and files_exist and symlink_exists)

    def test_directory_nopath(self):
        """no path."""
        start_path, final_path = self.setup_environment(files_dir=None,
                                                        exists=True)
        dir_exists, files_exist, symlink_exists = self.run_checks(start_path,
                                                                  final_path)
        dir_exists = os.path.exists(final_path)
        files_exist = len(os.listdir(final_path)) == 1 # just .gitignore
        self.assertTrue(dir_exists and files_exist)

    def test_symlink_broken_defaultpath(self):
        """sites/default/files is a broken symlink."""
        start_path, final_path = self.setup_environment(
                                          files_dir='sites/default/files',
                                          exists=False,
                                          symlink=True,
                                          name='sites/default/files',
                                          target='foo')
        dir_exists = os.path.exists(final_path)
        files_exist = len(os.listdir(final_path)) == 1 # just .gitignore
        self.assertTrue(dir_exists and files_exist)

    def setup_environment(self, files_dir, exists, symlink=False,
                                                   name=None,
                                                   target=None):
        """Create the necessary directory tree then various import scenarios

        For regular directories you should pass in:
            files_dir: Drupal file_directory_path variable value
                       (e.g. sites/default/files)
            exists: Bool. If the directory should exist.

        For symlinks you should pass in:
            symlink: True
            files_dir: Drupal file_directory_path variable value
                       (e.g. sites/default/files)
            exists: Bool. True = valid symlink, False = broken symlink
            name: The name of the symlink.
            target: where the symlink is targeted. if exist==true a symlink
                    with a relational (valid) path will be created.
                    If exists==False, the symlink will be left as-is (broken).

        """

        # Fake a return value for database file_directory_path variable.
        self.test_import.files_dir = files_dir

        # Normal path
        if not symlink:
            if exists and files_dir is not None:
                self._makedir(files_dir)
                self._makefiles(files_dir)
        # Symlink
        else:
            # Create valid target location for symlink
            if exists:
                pass
            else:
                self._makelink(name=name, target=target)
                import pdb
                pdb.set_trace()

        # Run import processing, suppress fabric errors (mysql will barf)
        with settings(hide('everything'), warn_only=True):
            self.test_import.setup_files_dir()

        # Return (Starting path, Final Path)
        if files_dir:
            start_path = os.path.join(self.working_dir, files_dir)
        else:
            start_path = None
        final_path = os.path.join(self.working_dir, 'sites/default/files')
        return (start_path, final_path)

    def run_checks(self, start_path, final_path):
        # Final path shouls exist.
        dir_exists = os.path.exists(final_path)
        # Two test files and a .gitignore should exist.
        files_exist = len(os.listdir(final_path)) == 3
        # Symlink should exist in old location, pointing to new location.
        if start_path:
            symlink_exists = os.path.islink(start_path) and os.path.realpath(start_path) == final_path
        else:
            symlink_exists = False
        return dir_exists, files_exist, symlink_exists

    def tearDown(self):
        """Cleanup.

        """
        shutil.rmtree(self.working_dir)

    def _makedir(self, d):
        """Create directory 'd' in working_dir. Acts like "mkdir -P"

        """
        os.makedirs(os.path.join(self.working_dir, d))

    def _makelink(self, name, target):
        """Create a symlink with name --> target in working_dir

        """
        name = os.path.join(self.working_dir, name)
        target = os.path.join(self.working_dir, target)
        if not os.path.isdir(os.path.dirname(name)):
            os.makedirs(os.path.dirname(name))
        os.symlink(target,name)

    def _makefiles(self, directory):
        """Create files in the files directory.

        """
        base = os.path.join(self.working_dir, directory)
        for i in range(2):
            with open(os.path.join(base, 'tmp%s.txt' % i), 'w') as f:
                f.write('Test_%s' % i)


    class TestImportTools(onramp.ImportTools):
        """Wrapper to make ImportTools test friendly.

        """
        def __init__(self, working_dir):
            """Override default importtools init and set only necessary vals.

            """
            self.working_dir = working_dir
            # This should be an invalid project so mysql doesn't make changes.
            self.project = 'invalidproject'

        def _get_files_dir(self):
            """Override and return an already known value.
            self.files_dir gets set during setup_environment

            """
            return self.files_dir


if __name__ == '__main__':
    unittest.main()

