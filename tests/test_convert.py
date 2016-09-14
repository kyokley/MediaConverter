import unittest
import mock
from subprocess import PIPE
from settings import ENCODER
from utils import EncoderException
from convert import (checkVideoEncoding,
                     fixMetaData,
                     _extractSubtitles,
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
        self.popen_patcher = mock.patch('convert.Popen')
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.log_patcher = mock.patch('convert.log')
        self.mock_log = self.log_patcher.start()
        self.addCleanup(self.log_patcher.stop)

        self.remove_patcher = mock.patch('convert.os.remove')
        self.mock_remove = self.remove_patcher.start()
        self.addCleanup(self.remove_patcher.stop)

        self.process1 = mock.MagicMock()
        self.process1.communicate.return_value = ('srt_stdout', 'srt_stderr')
        self.process1.returncode = 0

        self.process2 = mock.MagicMock()
        self.process2.communicate.return_value = ('vtt_stdout', 'vtt_stderr')
        self.mock_popen.side_effect = [self.process1, self.process2]
        self.process2.returncode = 0

        self.source = '/tmp/test_source.mkv'
        self.dest = '/tmp/test_dest.mp4'
        self.stream_identifier = '0:2'

    def test_success(self):
        _extractSubtitles(self.source,
                          self.dest,
                          self.stream_identifier,
                          )

        self.mock_popen.assert_any_call([ENCODER,
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
        self.assertTrue(self.process1.communicate.called)

        self.mock_popen.assert_any_call(['srt-vtt',
                                         '/tmp/test_dest.srt'],
                                        stdin=PIPE,
                                        stdout=PIPE,
                                        stderr=PIPE)
        self.assertTrue(self.process2.communicate.called)
        self.assertEqual(self.mock_popen.call_count, 2)

    def test_subtitle_extract_failed(self):
        self.process1.returncode = 1

        self.assertRaises(EncoderException,
                          _extractSubtitles,
                          self.source,
                          self.dest,
                          self.stream_identifier,
                          )

        self.mock_popen.assert_any_call([ENCODER,
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
        self.assertTrue(self.process1.communicate.called)
        self.assertTrue(self.mock_remove.called)
        self.assertEqual(self.mock_popen.call_count, 1)

    def test_vtt_extract_failed(self):
        self.process2.returncode = 1

        self.assertRaises(EncoderException,
                          _extractSubtitles,
                          self.source,
                          self.dest,
                          self.stream_identifier,
                          )

        self.mock_popen.assert_any_call([ENCODER,
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

        self.mock_popen.assert_any_call(['srt-vtt',
                                         '/tmp/test_dest.srt'],
                                        stdin=PIPE,
                                        stdout=PIPE,
                                        stderr=PIPE)
        self.assertTrue(self.process1.communicate.called)
        self.assertTrue(self.process2.communicate.called)
        self.assertTrue(self.mock_remove.called)
        self.assertEqual(self.mock_popen.call_count, 2)


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
