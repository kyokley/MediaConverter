import unittest
import mock

from utils import (stripUnicode,
                   is_valid_media_file,
                   is_valid_subtitle_file,
                   file_ext,
                   )

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

class TestIsValidMediaFile(unittest.TestCase):
    def setUp(self):
        self.exists_patcher = mock.patch('utils.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.MEDIA_FILE_EXTENSIONS_patcher = mock.patch('utils.MEDIA_FILE_EXTENSIONS', ('.mp4',))
        self.MEDIA_FILE_EXTENSIONS_patcher.start()

        self.mock_exists.return_value = True

    def tearDown(self):
        self.exists_patcher.stop()
        self.MEDIA_FILE_EXTENSIONS_patcher.stop()

    def test_file_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = False
        actual = is_valid_media_file('test_path.mp4')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.mp4')

    def test_bad_extension(self):
        expected = False
        actual = is_valid_media_file('test_path.txt')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.txt')

    def test_valid(self):
        expected = True
        actual = is_valid_media_file('test_path.mp4')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.mp4')

    def test_ignored_case(self):
        expected = True
        actual = is_valid_media_file('test_path.MP4')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.MP4')


class TestIsValidSubtitleFile(unittest.TestCase):
    def setUp(self):
        self.exists_patcher = mock.patch('utils.os.path.exists')
        self.mock_exists = self.exists_patcher.start()

        self.SUBTITLE_EXTENSIONS_patcher = mock.patch('utils.SUBTITLE_EXTENSIONS', ('.srt',))
        self.SUBTITLE_EXTENSIONS_patcher.start()

        self.mock_exists.return_value = True

    def tearDown(self):
        self.exists_patcher.stop()
        self.SUBTITLE_EXTENSIONS_patcher.stop()

    def test_file_does_not_exist(self):
        self.mock_exists.return_value = False

        expected = False
        actual = is_valid_subtitle_file('test_path.srt')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.srt')

    def test_bad_extension(self):
        expected = False
        actual = is_valid_subtitle_file('test_path.txt')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.txt')

    def test_valid(self):
        expected = True
        actual = is_valid_subtitle_file('test_path.srt')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.srt')

    def test_ignored_case(self):
        expected = True
        actual = is_valid_subtitle_file('test_path.SRT')

        self.assertEqual(expected, actual)
        self.mock_exists.assert_called_once_with('test_path.SRT')

class TestFileExt(unittest.TestCase):
    def test_file_ext(self):
        expected = '.mp4'
        actual = file_ext('test_path.mp4')

        self.assertEqual(expected, actual)