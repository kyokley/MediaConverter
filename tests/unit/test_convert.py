import pytest
import mock
import shlex
from pathlib import Path
from subprocess import PIPE
from settings import ENCODER
from utils import EncoderException
from convert import (
    checkVideoEncoding,
    _extractSubtitles,
    _extractSubtitleFromVideo,
    _convertSrtToVtt,
    _moveSubtitleFile,
    overwriteExistingFile,
    makeFileStreamable,
    encode,
    _reencodeVideo,
)


class TestCheckVideoEncoding:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_popen = mocker.patch("convert.Popen")

        self.mock_log = mocker.patch("convert.log")

        self.process = mock.MagicMock()
        self.mock_popen.return_value = self.process

        self.source = "test.mkv"

    def test_bad_call(self):
        self.process.communicate.return_value = ("stdout", INVALID_SAMPLE_OUTPUT)

        with pytest.raises(EncoderException):
            checkVideoEncoding(source=self.source)

        self.mock_popen.assert_called_once_with(
            (ENCODER, "-hide_banner", "-i", self.source), stderr=PIPE
        )
        self.mock_log.error.assert_called_once_with(INVALID_SAMPLE_OUTPUT.decode())

    def test_good_call(self):
        self.process.communicate.return_value = ("stdout", VALID_SAMPLE_OUTPUT)

        vres, ares, sres, surround = checkVideoEncoding(self.source)
        assert vres == 1
        assert ares == 0
        assert sres is not None


class TestExtractSubtitles:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_extractSubtitleFromVideo = mocker.patch(
            "convert._extractSubtitleFromVideo"
        )

        self.mock_convertSrtToVtt = mocker.patch("convert._convertSrtToVtt")

    def test_extract_subtitles(self):
        source = Path("/path/to/file.mp4")
        dest = Path("tmpfile.mp4")
        stream_identifier = "0:1"

        expected_srt = Path("tmpfile.srt")

        _extractSubtitles(source, dest, stream_identifier)

        self.mock_extractSubtitleFromVideo.assert_called_once_with(
            source, stream_identifier, expected_srt
        )
        self.mock_convertSrtToVtt.assert_called_once_with(expected_srt)


class TestExtractSubtitleFromVideo:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_popen = mocker.patch("convert.Popen")

        self.mock_log = mocker.patch("convert.log")

        self.process = mock.MagicMock()
        self.process.communicate.return_value = ("srt_stdout", "srt_stderr")
        self.process.returncode = 0

        self.mock_popen.return_value = self.process

        self.source = Path("/tmp/test_source.mkv")  # nosec
        self.dest = Path("/tmp/test_dest.mp4")  # nosec
        self.stream_identifier = "0:2"

    def test_success(self):
        _extractSubtitleFromVideo(
            self.source,
            self.stream_identifier,
            "/tmp/test_dest.srt",  # nosec
        )

        self.mock_popen.assert_called_once_with(
            [
                ENCODER,
                "-hide_banner",
                "-y",
                "-i",
                str(self.source),
                "-map",
                "0:2",
                "/tmp/test_dest.srt",  # nosec
            ],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )
        assert self.process.communicate.called

    def test_subtitle_extract_failed(self):
        self.process.returncode = 1

        with pytest.raises(EncoderException):
            _extractSubtitles(
                self.source,
                self.dest,
                self.stream_identifier,
            )

        self.mock_popen.assert_called_once_with(
            [
                ENCODER,
                "-hide_banner",
                "-y",
                "-i",
                str(self.source),
                "-map",
                "0:2",
                "/tmp/test_dest.srt",  # nosec
            ],
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )
        assert self.process.communicate.called


class TestConvertSrtToVtt:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_popen = mocker.patch("convert.Popen")

        self.mock_log = mocker.patch("convert.log")

        self.process = mock.MagicMock()
        self.process.communicate.return_value = ("vtt_stdout", "vtt_stderr")
        self.process.returncode = 0

        self.mock_popen.return_value = self.process

        self.srt_filename = Path("/path/to/file.srt")

    def test_success(self):
        expected = Path("/path/to/file.vtt")
        actual = _convertSrtToVtt(self.srt_filename)

        self.mock_popen.assert_called_once_with(
            ["srt-vtt", "/path/to/file.srt"], stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        self.process.communicate.assert_called_once_with()
        assert expected == actual

    def test_vtt_extract_failed(self):
        self.process.returncode = 1

        with pytest.raises(EncoderException):
            _convertSrtToVtt(self.srt_filename)

        self.mock_popen.assert_called_once_with(
            ["srt-vtt", "/path/to/file.srt"], stdin=PIPE, stdout=PIPE, stderr=PIPE
        )
        self.process.communicate.assert_called_once_with()


class TouchFileMixin:
    @staticmethod
    def _touch_file(path):
        with open(path, "w"):
            pass


class TestMoveSubtitleFile(TouchFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        self.mock_log = mocker.patch("convert.log")

        self.mock_move = mocker.patch("convert.shutil.move")

        self.source = temp_directory / "tmpfile.mp4"
        self.dest = temp_directory / "this.is.a.file.mp4"

    def test_subtitle_does_not_exist_no_dryRun(self):
        _moveSubtitleFile(self.source, self.dest, dryRun=False)
        assert not self.mock_move.called

    def test_subtitle_does_not_exist_dryRun(self):
        _moveSubtitleFile(self.source, self.dest, dryRun=True)
        assert not self.mock_move.called

    def test_subtitle_exists_no_dryRun(self):
        self._touch_file(self.source.with_suffix(".vtt"))
        _moveSubtitleFile(self.source, self.dest, dryRun=False)
        self.mock_move.assert_called_once_with(
            self.source.with_suffix(".vtt"),
            self.dest.with_suffix(".vtt"),
        )

    def test_subtitle_exists_dryRun(self):
        self._touch_file(self.source.with_suffix(".vtt"))
        _moveSubtitleFile(self.source, self.dest, dryRun=True)
        assert not self.mock_move.called


class TestOverwriteExistingFile(TouchFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        self.temp_directory = temp_directory
        mocker.patch("convert.MEDIAVIEWER_SUFFIX", "suffix.mp4")

        self.mock_log = mocker.patch("convert.log")

        self.mock_move = mocker.patch("convert.shutil.move")

        self.source = self.temp_directory / "tmpfile.mp4"

    def test_noDryRun_noSuffix(self, temp_directory):
        expected_dest = temp_directory / "tmpfile.mp4"

        res = overwriteExistingFile(
            self.source,
            temp_directory,
            dryRun=False,
            appendSuffix=False,
        )
        self.mock_move.assert_called_once_with(
            self.source,
            expected_dest,
        )
        assert res == expected_dest

    def test_dryRun_noSuffix(self, temp_directory):
        res = overwriteExistingFile(
            self.source,
            temp_directory,
            dryRun=True,
            appendSuffix=False,
        )
        assert not self.mock_move.called
        assert res == temp_directory / "tmpfile.mp4"

    def test_noDryRun_suffix(self, temp_directory):
        res = overwriteExistingFile(
            self.source,
            temp_directory,
            dryRun=False,
            appendSuffix=True,
        )
        self.mock_move.assert_called_once_with(
            self.temp_directory / "tmpfile.mp4",
            temp_directory / "tmpfile.mp4.suffix.mp4",
        )
        assert res == temp_directory / "tmpfile.mp4.suffix.mp4"

    def test_dryRun_suffix(self, temp_directory):
        res = overwriteExistingFile(
            self.source,
            temp_directory,
            dryRun=True,
            appendSuffix=True,
        )
        assert not self.mock_move.called
        assert res == temp_directory / f"{self.source.name}.suffix.mp4"


class TestMakeFileStreamable(TouchFileMixin):
    @pytest.fixture(autouse=True)
    def setUp(self, mocker, temp_directory):
        self.temp_directory = temp_directory
        self.mock_log = mocker.patch("convert.log")

        self.mock_encode = mocker.patch("convert.encode")

        self.mock_overwriteExistingFile = mocker.patch("convert.overwriteExistingFile")
        self.mock_overwriteExistingFile.return_value = "the_final_destination"

    def test_args_are_passed_along(self):
        dryRunSentinel = object()
        appendSuffixSentinel = object()
        orig = self.temp_directory / "this.is.a.file.mkv"
        self._touch_file(orig)
        res = makeFileStreamable(
            orig,
            dryRun=dryRunSentinel,
            appendSuffix=appendSuffixSentinel,
        )
        assert res == "the_final_destination"
        self.mock_encode.assert_called_once_with(
            self.temp_directory / "this.is.a.file.mkv",
            Path("/tmp/this.is.a.file.mp4"),
            dryRun=dryRunSentinel,
        )
        self.mock_overwriteExistingFile.assert_called_once_with(
            Path("/tmp/this.is.a.file.mp4"),
            self.temp_directory,
            dryRun=dryRunSentinel,
            appendSuffix=appendSuffixSentinel,
        )


class TestEncode:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_checkVideoEncoding = mocker.patch("convert.checkVideoEncoding")

        self.mock_handleSubtitles = mocker.patch("convert._handleSubtitles")

        self.mock_reencodeVideo = mocker.patch("convert._reencodeVideo")

        self.mock_vres = mock.MagicMock()
        self.mock_ares = mock.MagicMock()
        self.mock_sres = mock.MagicMock()
        self.mock_surround = mock.MagicMock()

        self.mock_checkVideoEncoding.return_value = (
            self.mock_vres,
            self.mock_ares,
            self.mock_sres,
            self.mock_surround,
        )

    def test_(self):
        dryRunSentinel = object()

        source = "/path/to/file.mkv"
        dest = "tmpfile.mp4"

        encode(source, dest, dryRun=dryRunSentinel)

        self.mock_checkVideoEncoding.assert_called_once_with(source)
        self.mock_handleSubtitles.assert_called_once_with(source, dest, self.mock_sres)
        self.mock_reencodeVideo.assert_called_once_with(
            source,
            dest,
            self.mock_vres,
            self.mock_ares,
            self.mock_surround,
            dryRun=dryRunSentinel,
        )


class TestReencodeVideo:
    @pytest.fixture(autouse=True)
    def setUp(self, mocker):
        self.mock_Popen = mocker.patch("convert.Popen")
        self.mock_Popen.return_value.returncode = 0

        mocker.patch("convert.ENCODER", "test_encoder")

    def test_small_vres_ares(self):
        expected = None
        actual = _reencodeVideo("test_source", "test_dest", True, True, False)

        assert expected == actual
        self.mock_Popen.assert_called_once_with(
            tuple(
                shlex.split(
                    "test_encoder -hide_banner -y -i test_source -c copy -pix_fmt yuv420p -movflags faststart test_dest"
                )
            ),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    def test_small_vres_no_ares(self):
        expected = None
        actual = _reencodeVideo("test_source", "test_dest", True, False, False)

        assert expected == actual
        self.mock_Popen.assert_called_once_with(
            tuple(
                shlex.split(
                    "test_encoder -hide_banner -y "
                    "-i test_source -c:v copy -c:a libfdk_aac -pix_fmt yuv420p -movflags faststart test_dest"
                )
            ),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    def test_small_no_vres_no_ares(self):
        expected = None
        actual = _reencodeVideo("test_source", "test_dest", False, False, False)

        assert expected == actual
        self.mock_Popen.assert_called_once_with(
            tuple(
                shlex.split(
                    "test_encoder -hide_banner -y "
                    "-i test_source -c:v libx264 "
                    "-c:a libfdk_aac -pix_fmt yuv420p -movflags faststart test_dest"
                )
            ),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    def test_large_vres_ares(self):
        expected = None
        actual = _reencodeVideo("test_source", "test_dest", True, True, False)

        assert expected == actual
        self.mock_Popen.assert_called_once_with(
            tuple(
                shlex.split(
                    "test_encoder -hide_banner -y "
                    "-i test_source -c copy -pix_fmt yuv420p -movflags faststart test_dest"
                )
            ),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    def test_large_vres_no_ares(self):
        expected = None
        actual = _reencodeVideo("test_source", "test_dest", True, False, False)

        assert expected == actual
        self.mock_Popen.assert_called_once_with(
            tuple(
                shlex.split(
                    "test_encoder -hide_banner -y "
                    "-i test_source -c:v copy "
                    "-c:a libfdk_aac -pix_fmt yuv420p -movflags faststart test_dest"
                )
            ),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )

    def test_large_no_vres_no_ares(self):
        expected = None
        actual = _reencodeVideo("test_source", "test_dest", False, False, False)

        assert expected == actual
        self.mock_Popen.assert_called_once_with(
            tuple(
                shlex.split(
                    "test_encoder -hide_banner -y "
                    "-i test_source "
                    "-c:v libx264 -c:a libfdk_aac -pix_fmt yuv420p -movflags faststart test_dest"
                )
            ),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
        )


VALID_SAMPLE_OUTPUT = b"""
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
"""

INVALID_SAMPLE_OUTPUT = b"""
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
"""
