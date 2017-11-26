import unittest
import mock

from utils import stripUnicode

class TestStripUnicode(unittest.TestCase):
    def setUp(self):
        self.unidecode_patcher = mock.patch('utils.unidecode')
        self.mock_unidecode = self.unidecode_patcher.start()

        self.getcwd_patcher = mock.patch('utils.os.getcwd')
        self.mock_getcwd = self.getcwd_patcher.start()

        self.chdir_patcher = mock.patch('utils.os.chdir')
        self.mock_chdir = self.chdir_patcher.start()

        self.rename_patcher = mock.patch('utils.os.rename')
        self.mock_rename = self.rename_patcher.start()

    def tearDown(self):
        self.unidecode_patcher.stop()
        self.getcwd_patcher.stop()
        self.chdir_patcher.stop()
        self.rename_patcher.stop()

    def test_no_changes(self):
        self.mock_unidecode.return_value = 'test_filename'

        expected = 'test_filename'
        actual = stripUnicode('test_filename')

        self.assertEqual(expected, actual)
        self.assertFalse(self.mock_chdir.called)
        self.assertFalse(self.mock_getcwd.called)
        self.assertFalse(self.mock_rename.called)

    def test_with_changes(self):
        self.mock_unidecode.return_value = 'test_stripped_filename'

        expected = 'test_stripped_filename'
        actual = stripUnicode('test_filename')

        self.assertEqual(expected, actual)
        self.assertFalse(self.mock_getcwd.called)
        self.assertFalse(self.mock_chdir.called)
        self.mock_rename.assert_called_once_with('test_filename',
                                                 'test_stripped_filename')

    def test_strip_apostrophe(self):
        self.mock_unidecode.return_value = "it's got an apostrophe"

        expected = "its got an apostrophe"
        actual = stripUnicode("it's got an apostrophe")

        self.assertEqual(expected, actual)
        self.assertFalse(self.mock_getcwd.called)
        self.assertFalse(self.mock_chdir.called)
        self.mock_rename.assert_called_once_with("it's got an apostrophe",
                                                 "its got an apostrophe")

    def test_with_path(self):
        self.mock_unidecode.return_value = 'test_stripped_filename'

        expected = '/new/path/test_stripped_filename'
        actual = stripUnicode('test_filename', path='/new/path')

        self.assertEqual(expected, actual)
        self.mock_chdir.assert_has_calls([mock.call('/new/path'),
                                          mock.call(self.mock_getcwd.return_value)])
        self.mock_getcwd.assert_called_once_with()
        self.mock_rename.assert_called_once_with('test_filename',
                                                 'test_stripped_filename')
