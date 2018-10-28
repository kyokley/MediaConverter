import unittest
import mock
import tempfile
import os
import shutil
import shlex
from subprocess import PIPE
from settings import ENCODER
from utils import EncoderException
from convert import (checkVideoEncoding,
                     fixMetaData,
                     _extractSubtitles,
                     _extractSubtitleFromVideo,
                     _convertSrtToVtt,
                     _moveSubtitleFile,
                     _handleSubtitles,
                     overwriteExistingFile,
                     makeFileStreamable,
                     encode,
                     _getFilesInDirectory,
                     _reencodeVideo,
                     )

class TestCheckVideoEncoding(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = mock.patch('convert.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.process = mock.MagicMock()
        self.mock_popen.return_value = self.process

        self.source = 'test.mkv'

    def test_bad_call(self):
        self.process.communicate.return_value = ('stdout', INVALID_SAMPLE_OUTPUT)

        self.assertRaises(EncoderException,
                          callableObj=checkVideoEncoding,
                          source=self.source)

        self.mock_popen.assert_called_once_with((ENCODER,
                                                 '-hide_banner',
                                                 '-i',
                                                 self.source),
                                                stderr=PIPE)
        self.mock_log.error.assert_called_once_with(INVALID_SAMPLE_OUTPUT)

    def test_good_call(self):
        self.process.communicate.return_value = ('stdout', VALID_SAMPLE_OUTPUT)

        vres, ares, sres = checkVideoEncoding(self.source)
        self.assertEqual(vres, 1)
        self.assertEqual(ares, 0)
        self.assertFalse(sres is None)

class TestFixMetaData(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = mock.patch('convert.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.process = mock.MagicMock()
        self.mock_popen.return_value = self.process
        self.source = 'test.mkv'

    def test_dryRun(self):
        fixMetaData(self.source, dryRun=True)

        self.assertFalse(self.mock_popen.called)
        self.assertFalse(self.process.called)

    def test_noDryRun(self):
        fixMetaData(self.source, dryRun=False)

        self.mock_popen.assert_called_once_with(('qtfaststart',
                                                 self.source),
                                                stdin=PIPE,
                                                stdout=PIPE,
                                                stderr=PIPE)
        self.assertTrue(self.process.communicate.called)

class TestExtractSubtitles(unittest.TestCase):
    def setUp(self):
        self.extractSubtitleFromVideo_patcher = mock.patch('convert._extractSubtitleFromVideo')
        self.mock_extractSubtitleFromVideo = self.extractSubtitleFromVideo_patcher.start()
        self.addCleanup(self.extractSubtitleFromVideo_patcher.stop)

        self.convertSrtToVtt_patcher = mock.patch('convert._convertSrtToVtt')
        self.mock_convertSrtToVtt = self.convertSrtToVtt_patcher.start()
        self.addCleanup(self.convertSrtToVtt_patcher.stop)

    def test_(self):
        source = '/path/to/file.mp4'
        dest = 'tmpfile.mp4'
        stream_identifier = '0:1'

        expected_srt = 'tmpfile.srt'

        _extractSubtitles(source,
                          dest,
                          stream_identifier)

        self.mock_extractSubtitleFromVideo.assert_called_once_with(source,
                                                                   dest,
                                                                   stream_identifier,
                                                                   expected_srt)
        self.mock_convertSrtToVtt.assert_called_once_with(expected_srt)

class TestExtractSubtitleFromVideo(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = mock.patch('convert.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.remove_patcher = mock.patch('convert.os.remove')
        self.mock_remove = self.remove_patcher.start()
        self.addCleanup(self.remove_patcher.stop)

        self.process = mock.MagicMock()
        self.process.communicate.return_value = ('srt_stdout', 'srt_stderr')
        self.process.returncode = 0

        self.mock_popen.return_value = self.process

        self.source = '/tmp/test_source.mkv'
        self.dest = '/tmp/test_dest.mp4'
        self.stream_identifier = '0:2'

    def test_success(self):
        _extractSubtitleFromVideo(self.source,
                                  self.dest,
                                  self.stream_identifier,
                                  '/tmp/test_dest.srt',
                                  )

        self.mock_popen.assert_called_once_with([ENCODER,
                                                 '-hide_banner',
                                                 '-y',
                                                 '-i',
                                                 self.source,
                                                 '-map',
                                                 '0:2',
                                                 '/tmp/test_dest.srt'],
                                                stdin=PIPE,
                                                stdout=PIPE,
                                                stderr=PIPE)
        self.assertTrue(self.process.communicate.called)

    def test_subtitle_extract_failed(self):
        self.process.returncode = 1

        self.assertRaises(EncoderException,
                          _extractSubtitles,
                          self.source,
                          self.dest,
                          self.stream_identifier,
                          )

        self.mock_popen.assert_called_once_with([ENCODER,
                                                 '-hide_banner',
                                                 '-y',
                                                 '-i',
                                                 self.source,
                                                 '-map',
                                                 '0:2',
                                                 '/tmp/test_dest.srt'],
                                                stdin=PIPE,
                                                stdout=PIPE,
                                                stderr=PIPE)
        self.assertTrue(self.process.communicate.called)
        self.assertTrue(self.mock_remove.called)

class TestConvertSrtToVtt(unittest.TestCase):
    def setUp(self):
        self.popen_patcher = mock.patch('convert.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.remove_patcher = mock.patch('convert.os.remove')
        self.mock_remove = self.remove_patcher.start()
        self.addCleanup(self.remove_patcher.stop)

        self.process = mock.MagicMock()
        self.process.communicate.return_value = ('vtt_stdout', 'vtt_stderr')
        self.process.returncode = 0

        self.mock_popen.return_value = self.process

        self.srt_filename = '/path/to/file.srt'

    def test_success(self):
        expected = '/path/to/file.vtt'
        actual = _convertSrtToVtt(self.srt_filename)

        self.mock_popen.assert_called_once_with(['srt-vtt',
                                                 '/path/to/file.srt'],
                                                stdin=PIPE,
                                                stdout=PIPE,
                                                stderr=PIPE)
        self.process.communicate.assert_called_once_with()
        self.assertFalse(self.mock_remove.called)
        self.assertEqual(expected, actual)

    def test_vtt_extract_failed(self):
        self.process.returncode = 1

        self.assertRaises(EncoderException,
                          _convertSrtToVtt,
                          self.srt_filename,
                          )

        self.mock_popen.assert_called_once_with(['srt-vtt',
                                                 '/path/to/file.srt'],
                                                stdin=PIPE,
                                                stdout=PIPE,
                                                stderr=PIPE)
        self.process.communicate.assert_called_once_with()
        self.mock_remove.assert_called_once_with('/path/to/file.vtt')

class TestMoveSubtitleFile(unittest.TestCase):
    def setUp(self):
        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.exists_patcher = mock.patch('convert.os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.addCleanup(self.exists_patcher.stop)

        self.remove_patcher = mock.patch('convert.os.remove')
        self.mock_remove = self.remove_patcher.start()
        self.addCleanup(self.remove_patcher.stop)

        self.move_patcher = mock.patch('convert.shutil.move')
        self.mock_move = self.move_patcher.start()
        self.addCleanup(self.move_patcher.stop)

        self.source = 'tmpfile.mp4'
        self.dest = '/tmp/this.is.a.file.mp4'

    def test_subtitle_does_not_exist_no_dryRun(self):
        self.mock_exists.return_value = False
        _moveSubtitleFile(self.source,
                          self.dest,
                          dryRun=False)
        self.mock_exists.assert_called_once_with('tmpfile.vtt')
        self.assertFalse(self.mock_move.called)
        self.assertFalse(self.mock_remove.called)

    def test_subtitle_does_not_exist_dryRun(self):
        self.mock_exists.return_value = False
        _moveSubtitleFile(self.source,
                          self.dest,
                          dryRun=True)
        self.mock_exists.assert_called_once_with('tmpfile.vtt')
        self.assertFalse(self.mock_move.called)
        self.assertFalse(self.mock_remove.called)

    def test_subtitle_exists_no_dryRun(self):
        self.mock_exists.return_value = True
        _moveSubtitleFile(self.source,
                          self.dest,
                          dryRun=False)
        self.mock_exists.assert_called_once_with('tmpfile.vtt')
        self.mock_move.assert_called_once_with('tmpfile.vtt', '/tmp/this.is.a.file.vtt')
        self.mock_remove.assert_called_once_with('tmpfile.srt')

    def test_subtitle_exists_dryRun(self):
        self.mock_exists.return_value = True
        _moveSubtitleFile(self.source,
                          self.dest,
                          dryRun=True)
        self.mock_exists.assert_called_once_with('tmpfile.vtt')
        self.assertFalse(self.mock_move.called)
        self.assertFalse(self.mock_remove.called)

@mock.patch('convert.MEDIAVIEWER_SUFFIX', '%s.suffix.mp4')
class TestOverwriteExistingFile(unittest.TestCase):
    def setUp(self):
        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.exists_patcher = mock.patch('convert.os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.addCleanup(self.exists_patcher.stop)

        self.remove_patcher = mock.patch('convert.os.remove')
        self.mock_remove = self.remove_patcher.start()
        self.addCleanup(self.remove_patcher.stop)

        self.move_patcher = mock.patch('convert.shutil.move')
        self.mock_move = self.move_patcher.start()
        self.addCleanup(self.move_patcher.stop)

        self.moveSubtitleFile_patcher = mock.patch('convert._moveSubtitleFile')
        self.mock_moveSubtitleFile = self.moveSubtitleFile_patcher.start()
        self.addCleanup(self.moveSubtitleFile_patcher.stop)

        self.mock_exists.return_value = True

        self.source = 'tmpfile.mp4'
        self.dest = '/tmp/this.is.a.file.mp4'

    def test_keepOriginal_noDryRun_noSuffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=False,
                                    dryRun=False,
                                    appendSuffix=False)
        self.assertFalse(self.mock_remove.called)
        self.mock_move.assert_called_once_with('tmpfile.mp4',
                                               '/tmp/this.is.a.file.mp4')
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4',
                                                           dryRun=False)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4')

    def test_removeOriginal_noDryRun_noSuffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=True,
                                    dryRun=False,
                                    appendSuffix=False)
        self.mock_remove.assert_called_once_with('/tmp/this.is.a.file.mp4')
        self.mock_move.assert_called_once_with('tmpfile.mp4',
                                               '/tmp/this.is.a.file.mp4')
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4',
                                                           dryRun=False)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4')

    def test_keepOriginal_dryRun_noSuffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=False,
                                    dryRun=True,
                                    appendSuffix=False)
        self.assertFalse(self.mock_remove.called)
        self.assertFalse(self.mock_move.called)
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4',
                                                           dryRun=True)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4')

    def test_removeOriginal_dryRun_noSuffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=True,
                                    dryRun=True,
                                    appendSuffix=False)
        self.assertFalse(self.mock_remove.called)
        self.assertFalse(self.mock_move.called)
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4',
                                                           dryRun=True)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4')

    def test_keepOriginal_noDryRun_suffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=False,
                                    dryRun=False,
                                    appendSuffix=True)
        self.assertFalse(self.mock_remove.called)
        self.mock_move.assert_called_once_with('tmpfile.mp4',
                                               '/tmp/this.is.a.file.mp4.suffix.mp4')
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4.suffix.mp4',
                                                           dryRun=False)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4.suffix.mp4')

    def test_removeOriginal_noDryRun_suffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=True,
                                    dryRun=False,
                                    appendSuffix=True)
        self.mock_remove.assert_called_once_with('/tmp/this.is.a.file.mp4')
        self.mock_move.assert_called_once_with('tmpfile.mp4',
                                               '/tmp/this.is.a.file.mp4.suffix.mp4')
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4.suffix.mp4',
                                                           dryRun=False)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4.suffix.mp4')

    def test_keepOriginal_dryRun_suffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=False,
                                    dryRun=True,
                                    appendSuffix=True)
        self.assertFalse(self.mock_remove.called)
        self.assertFalse(self.mock_move.called)
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4.suffix.mp4',
                                                           dryRun=True)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4.suffix.mp4')

    def test_removeOriginal_dryRun_suffix(self):
        res = overwriteExistingFile('tmpfile.mp4',
                                    '/tmp/this.is.a.file.mp4',
                                    removeOriginal=True,
                                    dryRun=True,
                                    appendSuffix=True)
        self.assertFalse(self.mock_remove.called)
        self.assertFalse(self.mock_move.called)
        self.mock_moveSubtitleFile.assert_called_once_with('tmpfile.mp4',
                                                           '/tmp/this.is.a.file.mp4.suffix.mp4',
                                                           dryRun=True)
        self.assertEqual(res, '/tmp/this.is.a.file.mp4.suffix.mp4')

class TestMakeFileStreamable(unittest.TestCase):
    def setUp(self):
        self.realpath_patcher = mock.patch('convert.os.path.realpath')
        self.mock_realpath = self.realpath_patcher.start()
        self.mock_realpath.return_value = 'orig_filename'
        self.addCleanup(self.realpath_patcher.stop)

        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.encode_patcher = mock.patch('convert.encode')
        self.mock_encode = self.encode_patcher.start()
        self.addCleanup(self.encode_patcher.stop)

        self.fixMetaData_patcher = mock.patch('convert.fixMetaData')
        self.mock_fixMetaData = self.fixMetaData_patcher.start()
        self.addCleanup(self.fixMetaData_patcher.stop)

        self.overwriteExistingFile_patcher = mock.patch('convert.overwriteExistingFile')
        self.mock_overwriteExistingFile = self.overwriteExistingFile_patcher.start()
        self.mock_overwriteExistingFile.return_value = 'the_final_destination'
        self.addCleanup(self.overwriteExistingFile_patcher.stop)

    def test_args_are_passed_along(self):
        dryRunSentinel = object()
        appendSuffixSentinel = object()
        removeOriginalSentinel = object()
        res = makeFileStreamable('/tmp/this.is.a.file.mkv',
                                 dryRun=dryRunSentinel,
                                 appendSuffix=appendSuffixSentinel,
                                 removeOriginal=removeOriginalSentinel)
        self.assertEqual(res, 'the_final_destination')
        self.mock_realpath.assert_called_once_with('/tmp/this.is.a.file.mkv')
        self.mock_encode.assert_called_once_with('orig_filename',
                                                 'tmpfile.mp4',
                                                 dryRun=dryRunSentinel)
        self.mock_fixMetaData.assert_called_once_with('tmpfile.mp4',
                                                      dryRun=dryRunSentinel)
        self.mock_overwriteExistingFile.assert_called_once_with('tmpfile.mp4',
                                                                'orig_filename',
                                                                dryRun=dryRunSentinel,
                                                                appendSuffix=appendSuffixSentinel,
                                                                removeOriginal=removeOriginalSentinel)

class TestEncode(unittest.TestCase):
    def setUp(self):
        self.checkVideoEncoding_patcher = mock.patch('convert.checkVideoEncoding')
        self.mock_checkVideoEncoding = self.checkVideoEncoding_patcher.start()
        self.addCleanup(self.checkVideoEncoding_patcher.stop)

        self.handleSubtitle_patcher = mock.patch('convert._handleSubtitles')
        self.mock_handleSubtitles = self.handleSubtitle_patcher.start()
        self.addCleanup(self.handleSubtitle_patcher.stop)

        self.reencodeVideo_patcher = mock.patch('convert._reencodeVideo')
        self.mock_reencodeVideo = self.reencodeVideo_patcher.start()
        self.addCleanup(self.reencodeVideo_patcher.stop)

        self.mock_vres = mock.MagicMock()
        self.mock_ares = mock.MagicMock()
        self.mock_sres = mock.MagicMock()

        self.mock_checkVideoEncoding.return_value = (self.mock_vres,
                                                     self.mock_ares,
                                                     self.mock_sres)

    def test_(self):
        dryRunSentinel = object()

        source = '/path/to/file.mkv'
        dest = 'tmpfile.mp4'

        encode(source, dest, dryRun=dryRunSentinel)

        self.mock_checkVideoEncoding.assert_called_once_with(source)
        self.mock_handleSubtitles.assert_called_once_with(source,
                                                          dest,
                                                          self.mock_sres)
        self.mock_reencodeVideo.assert_called_once_with(source,
                                                        dest,
                                                        self.mock_vres,
                                                        self.mock_ares,
                                                        dryRun=dryRunSentinel)

class TestHandleSubtitles(unittest.TestCase):
    def setUp(self):
        self.exists_patcher = mock.patch('convert.os.path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.addCleanup(self.exists_patcher.stop)

        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.convertSrtToVtt_patcher = mock.patch('convert._convertSrtToVtt')
        self.mock_convertSrtToVtt = self.convertSrtToVtt_patcher.start()
        self.addCleanup(self.convertSrtToVtt_patcher.stop)
        self.mock_convertSrtToVtt.return_value = '/path/to/English.vtt'

        self.moveSubtitleFile_patcher = mock.patch('convert._moveSubtitleFile')
        self.mock_moveSubtitleFile = self.moveSubtitleFile_patcher.start()
        self.addCleanup(self.moveSubtitleFile_patcher.stop)

        self.extractSubtitles_patcher = mock.patch('convert._extractSubtitles')
        self.mock_extractSubtitles = self.extractSubtitles_patcher.start()
        self.addCleanup(self.extractSubtitles_patcher.stop)

        self.source = '/path/to/file.mkv'
        self.dest = 'tmpfile.mp4'
        self.sres = mock.MagicMock()
        self.sres.groups.return_value = (3, 4)

    def test_EnglishSrtExists(self):
        self.mock_exists.side_effect = [True, False]

        _handleSubtitles(self.source, self.dest, self.sres)

        self.mock_exists.assert_has_calls([mock.call('/path/to/English.srt'),
                                           mock.call('/path/to/2_Eng.srt'),
                                           ])
        self.mock_convertSrtToVtt.assert_called_once_with('/path/to/English.srt')
        self.mock_moveSubtitleFile.assert_called_once_with('/path/to/English.vtt',
                                                           'tmpfile.vtt')
        self.assertFalse(self.mock_extractSubtitles.called)
        self.assertFalse(self.sres.groups.called)

    def test_2_EngSrtExists(self):
        self.mock_exists.side_effect = [False, True]

        _handleSubtitles(self.source, self.dest, self.sres)

        self.mock_exists.assert_has_calls([mock.call('/path/to/English.srt'),
                                           mock.call('/path/to/2_Eng.srt'),
                                           ])
        self.mock_convertSrtToVtt.assert_called_once_with('/path/to/2_Eng.srt')
        self.mock_moveSubtitleFile.assert_called_once_with('/path/to/English.vtt',
                                                           'tmpfile.vtt')
        self.assertFalse(self.mock_extractSubtitles.called)
        self.assertFalse(self.sres.groups.called)

    def test_FileSrtExists(self):
        self.mock_exists.side_effect = [False, False, True]
        self.mock_convertSrtToVtt.return_value = '/path/to/file.vtt'

        _handleSubtitles(self.source, self.dest, self.sres)

        self.mock_exists.assert_any_call('/path/to/English.srt')
        self.mock_exists.assert_any_call('/path/to/file.srt')
        self.mock_convertSrtToVtt.assert_called_once_with('/path/to/file.srt')
        self.mock_moveSubtitleFile.assert_called_once_with('/path/to/file.vtt',
                                                           'tmpfile.vtt')
        self.assertFalse(self.mock_extractSubtitles.called)
        self.assertFalse(self.sres.groups.called)

    def test_subtitleStreamInFile(self):
        self.mock_exists.return_value = False

        _handleSubtitles(self.source, self.dest, self.sres)

        self.mock_exists.assert_any_call('/path/to/English.srt')
        self.mock_exists.assert_any_call('/path/to/file.srt')
        self.assertFalse(self.mock_convertSrtToVtt.called)
        self.assertFalse(self.mock_moveSubtitleFile.called)
        self.sres.groups.assert_called_once_with()
        self.mock_extractSubtitles.assert_called_once_with(self.source,
                                                           self.dest,
                                                           '3:4')

    def test_noSubtitles(self):
        self.mock_exists.return_value = False

        _handleSubtitles(self.source, self.dest, None)

        self.mock_exists.assert_any_call('/path/to/English.srt')
        self.mock_exists.assert_any_call('/path/to/file.srt')
        self.assertFalse(self.mock_convertSrtToVtt.called)
        self.assertFalse(self.mock_moveSubtitleFile.called)
        self.assertFalse(self.mock_extractSubtitles.called)
        self.assertFalse(self.sres.groups.called)

class TestGetFilesInDirectory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_path_does_not_exist(self):
        non_existent_path = os.path.join(self.temp_dir, 'test_file')
        expected = set()
        actual = _getFilesInDirectory(non_existent_path)
        self.assertEqual(expected, actual)

    def test_path_is_empty(self):
        expected = set()
        actual = _getFilesInDirectory(self.temp_dir)
        self.assertEqual(expected, actual)

    def test_files_exist(self):
        files = [tempfile.mkstemp(dir=self.temp_dir)
                    for i in xrange(3)]
        expected = set([x[1] for x in files])
        actual = _getFilesInDirectory(self.temp_dir)
        self.assertEqual(expected, actual)

    def test_nested_files_exist(self):
        expected = set()
        dirs = [tempfile.mkdtemp(dir=self.temp_dir)
                    for i in xrange(3)]
        for dir in dirs:
            files = [tempfile.mkstemp(dir=dir)[1]
                        for i in xrange(3)]
            expected.update(files)

        actual = _getFilesInDirectory(self.temp_dir)
        self.assertEqual(expected, actual)

class TestReencodeVideo(unittest.TestCase):
    def setUp(self):
        self.getsize_patcher = mock.patch('convert.os.path.getsize')
        self.mock_getsize = self.getsize_patcher.start()

        self.Popen_patcher = mock.patch('convert.Popen')
        self.mock_Popen = self.Popen_patcher.start()
        self.mock_Popen.return_value.returncode = 0

        self.ENCODER_patcher = mock.patch('convert.ENCODER', 'test_encoder')
        self.ENCODER_patcher.start()

        self.mock_getsize.return_value = 1000

    def tearDown(self):
        self.getsize_patcher.stop()
        self.Popen_patcher.stop()
        self.ENCODER_patcher.stop()

    def test_small_vres_ares(self):
        expected = None
        actual = _reencodeVideo('test_source',
                                'test_dest',
                                True,
                                True)

        self.assertEqual(expected, actual)
        self.mock_Popen.assert_called_once_with(
                tuple(shlex.split(
                    'test_encoder -hide_banner -y -i test_source -c copy test_dest')),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE)

    def test_small_vres_no_ares(self):
        expected = None
        actual = _reencodeVideo('test_source',
                                'test_dest',
                                True,
                                False)

        self.assertEqual(expected, actual)
        self.mock_Popen.assert_called_once_with(
                tuple(shlex.split(
                    'test_encoder -hide_banner -y -i test_source -c:v copy -c:a libfdk_aac test_dest')),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE)

    def test_small_no_vres_no_ares(self):
        expected = None
        actual = _reencodeVideo('test_source',
                                'test_dest',
                                False,
                                False)

        self.assertEqual(expected, actual)
        self.mock_Popen.assert_called_once_with(
                tuple(shlex.split(
                    'test_encoder -hide_banner -y -i test_source -c:v libx264 -c:a libfdk_aac test_dest')),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE)

    def test_large_vres_ares(self):
        self.mock_getsize.return_value = 1024 * 1024 * 1024 * 3

        expected = None
        actual = _reencodeVideo('test_source',
                                'test_dest',
                                True,
                                True)

        self.assertEqual(expected, actual)
        self.mock_Popen.assert_called_once_with(
                tuple(shlex.split(
                    'test_encoder -hide_banner -y -i test_source -crf 30 -preset slow test_dest')),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE)

    def test_large_vres_no_ares(self):
        self.mock_getsize.return_value = 1024 * 1024 * 1024 * 3

        expected = None
        actual = _reencodeVideo('test_source',
                                'test_dest',
                                True,
                                False)

        self.assertEqual(expected, actual)
        self.mock_Popen.assert_called_once_with(
                tuple(shlex.split(
                    'test_encoder -hide_banner -y -i test_source -crf 30 -preset slow -c:a libfdk_aac test_dest')),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE)

    def test_large_no_vres_no_ares(self):
        self.mock_getsize.return_value = 1024 * 1024 * 1024 * 3

        expected = None
        actual = _reencodeVideo('test_source',
                                'test_dest',
                                False,
                                False)

        self.assertEqual(expected, actual)
        self.mock_Popen.assert_called_once_with(
                tuple(shlex.split(
                    'test_encoder -hide_banner -y -i test_source -crf 30 -preset slow -c:v libx264 -c:a libfdk_aac test_dest')),
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE)


VALID_SAMPLE_OUTPUT = '''
Input #0, matroska,webm, from '/tmp/test.mkv':
  Metadata:
    title           : Test
    encoder         : libebml v1.2.3 + libmatroska v1.3.0
    creation_time   : 2014-08-07 14:15:22
  Duration: 01:29:23.00, start: 0.000000, bitrate: 1753 kb/s
    Chapter #0:0: start 0.000000, end 217.280000
    Metadata:
      title           : Test
    Chapter #0:1: start 217.280000, end 368.840000
    Metadata:
      title           : Test
    Chapter #0:2: start 368.840000, end 527.240000
    Metadata:
      title           : Test
    Chapter #0:3: start 527.240000, end 723.560000
    Metadata:
      title           : Test
    Chapter #0:4: start 723.560000, end 948.680000
    Metadata:
      title           : Test
    Chapter #0:5: start 948.680000, end 1163.360000
    Metadata:
      title           : Test
    Chapter #0:6: start 1163.360000, end 1354.280000
    Metadata:
      title           : Test
    Chapter #0:7: start 1354.280000, end 1438.280000
    Metadata:
      title           : Test
    Chapter #0:8: start 1438.280000, end 1623.160000
    Metadata:
      title           : Test
    Chapter #0:9: start 1623.160000, end 1988.920000
    Metadata:
      title           : Test
    Chapter #0:10: start 1988.920000, end 2116.120000
    Metadata:
      title           : Test
    Chapter #0:11: start 2116.120000, end 2220.760000
    Metadata:
      title           : Test
    Chapter #0:12: start 2220.760000, end 2414.200000
    Metadata:
      title           : Test
    Chapter #0:13: start 2414.200000, end 2709.520000
    Metadata:
      title           : Test
    Chapter #0:14: start 2709.520000, end 2753.000000
    Metadata:
      title           : Test
    Chapter #0:15: start 2753.000000, end 2955.200000
    Metadata:
      title           : Test
    Chapter #0:16: start 2955.200000, end 3149.600000
    Metadata:
      title           : Test
    Chapter #0:17: start 3149.600000, end 3394.000000
    Metadata:
      title           : Test
    Chapter #0:18: start 3394.000000, end 3454.800000
    Metadata:
      title           : Test
    Chapter #0:19: start 3454.800000, end 3708.200000
    Metadata:
      title           : Test
    Chapter #0:20: start 3708.200000, end 3864.760000
    Metadata:
      title           : Test
    Chapter #0:21: start 3864.760000, end 4143.920000
    Metadata:
      title           : Test
    Chapter #0:22: start 4143.920000, end 4184.520000
    Metadata:
      title           : Test
    Chapter #0:23: start 4184.520000, end 4339.160000
    Metadata:
      title           : Test
    Chapter #0:24: start 4339.160000, end 4614.720000
    Metadata:
      title           : Test
    Chapter #0:25: start 4614.720000, end 4865.520000
    Metadata:
      title           : Test
    Chapter #0:26: start 4865.520000, end 5181.960000
    Metadata:
      title           : Test
    Chapter #0:27: start 5181.960000, end 5363.000000
    Metadata:
      title           : Test
    Stream #0:0(eng): Video: h264 (High), yuv420p, 668x404 [SAR 1:1 DAR 167:101], 25 fps, 25 tbr, 1k tbn, 50 tbc (default)
    Metadata:
      title           : Test
    Stream #0:1(eng): Audio: ac3, 48000 Hz, 5.0(side), fltp, 448 kb/s (default)
    Metadata:
      title           : English AC3 5.1 448 kbps
    Stream #0:2(ita): Subtitle: subrip (default)
    Metadata:
      title           : Sottotitoli SRT - Italiano
    Stream #0:3(eng): Subtitle: subrip
    Metadata:
      title           : Subtitle SRT - English
    Stream #0:4(spa): Subtitle: subrip
    Metadata:
      title           : Subtitle SRT - Spanish
At least one output file must be specified
'''

INVALID_SAMPLE_OUTPUT = '''
Input #0, matroska,webm, from '/tmp/test.mkv':
  Metadata:
    title           : Test
    encoder         : libebml v1.2.3 + libmatroska v1.3.0
    creation_time   : 2014-08-07 14:15:22
  Duration: 01:29:23.00, start: 0.000000, bitrate: 1753 kb/s
    Chapter #0:0: start 0.000000, end 217.280000
    Metadata:
      title           : Test
    Chapter #0:1: start 217.280000, end 368.840000
    Metadata:
      title           : Test
    Chapter #0:2: start 368.840000, end 527.240000
    Metadata:
      title           : Test
    Chapter #0:3: start 527.240000, end 723.560000
    Metadata:
      title           : Test
    Chapter #0:4: start 723.560000, end 948.680000
    Metadata:
      title           : Test
    Chapter #0:5: start 948.680000, end 1163.360000
    Metadata:
      title           : Test
    Chapter #0:6: start 1163.360000, end 1354.280000
    Metadata:
      title           : Test
    Chapter #0:7: start 1354.280000, end 1438.280000
    Metadata:
      title           : Test
    Chapter #0:8: start 1438.280000, end 1623.160000
    Metadata:
      title           : Test
    Chapter #0:9: start 1623.160000, end 1988.920000
    Metadata:
      title           : Test
    Chapter #0:10: start 1988.920000, end 2116.120000
    Metadata:
      title           : Test
    Chapter #0:11: start 2116.120000, end 2220.760000
    Metadata:
      title           : Test
    Chapter #0:12: start 2220.760000, end 2414.200000
    Metadata:
      title           : Test
    Chapter #0:13: start 2414.200000, end 2709.520000
    Metadata:
      title           : Test
    Chapter #0:14: start 2709.520000, end 2753.000000
    Metadata:
      title           : Test
    Chapter #0:15: start 2753.000000, end 2955.200000
    Metadata:
      title           : Test
    Chapter #0:16: start 2955.200000, end 3149.600000
    Metadata:
      title           : Test
    Chapter #0:17: start 3149.600000, end 3394.000000
    Metadata:
      title           : Test
    Chapter #0:18: start 3394.000000, end 3454.800000
    Metadata:
      title           : Test
    Chapter #0:19: start 3454.800000, end 3708.200000
    Metadata:
      title           : Test
    Chapter #0:20: start 3708.200000, end 3864.760000
    Metadata:
      title           : Test
    Chapter #0:21: start 3864.760000, end 4143.920000
    Metadata:
      title           : Test
    Chapter #0:22: start 4143.920000, end 4184.520000
    Metadata:
      title           : Test
    Chapter #0:23: start 4184.520000, end 4339.160000
    Metadata:
      title           : Test
    Chapter #0:24: start 4339.160000, end 4614.720000
    Metadata:
      title           : Test
    Chapter #0:25: start 4614.720000, end 4865.520000
    Metadata:
      title           : Test
    Chapter #0:26: start 4865.520000, end 5181.960000
    Metadata:
      title           : Test
    Chapter #0:27: start 5181.960000, end 5363.000000
    Metadata:
      title           : Test
    Stream #0:0(eng): Video: h264 (High), yuv420p, 668x404 [SAR 1:1 DAR 167:101], 25 fps, 25 tbr, 1k tbn, 50 tbc (default)
    Metadata:
      title           : Test
    Stream #0:1(eng): Audio: ac3, 48000 Hz, 5.0(side), fltp, 448 kb/s (default)
    Metadata:
      title           : English AC3 5.1 448 kbps
    Stream #0:2(ita): Subtitle: subrip (default)
    Metadata:
      title           : Sottotitoli SRT - Italiano
    Stream #0:3(eng): Subtitle: subrip
    Metadata:
      title           : Subtitle SRT - English
    Stream #0:4(spa): Subtitle: subrip
    Metadata:
      title           : Subtitle SRT - Spanish
Stream map '0:s:3' matches no streams.
To ignore this, add a trailing '?' to the map.
'''
