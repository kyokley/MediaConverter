from pathlib import Path
from re import match

import pytest

import convert
import utils
from settings import MEDIAVIEWER_SUFFIX
from tv_runner import TvRunner


def test_directory_move_qualifies_generic_sidecars_and_preserves_contents(
    tmp_path, monkeypatch
):
    root = tmp_path / "library"
    root.mkdir()
    for name, data in (("One", b"one"), ("Two", b"two")):
        folder = root / name
        folder.mkdir()
        (folder / f"{name}.mp4").write_bytes(b"video")
        (folder / "2_Eng.srt").write_bytes(data)
    monkeypatch.setattr("tv_runner.MINIMUM_FILE_SIZE", 0)

    TvRunner().handleDirs(root)

    assert (root / "One.2_Eng.srt").read_bytes() == b"one"
    assert (root / "Two.2_Eng.srt").read_bytes() == b"two"
    assert utils.matching_subtitle_files(root / "One.mp4") == [root / "One.2_Eng.srt"]


def test_directory_move_collision_keeps_video_and_sidecar(tmp_path, monkeypatch):
    root = tmp_path / "library"
    root.mkdir()
    folder = root / "One"
    folder.mkdir()
    video = folder / "One.mp4"
    sidecar = folder / "One.en.srt"
    video.write_bytes(b"video")
    sidecar.write_bytes(b"subtitle")
    (root / "One.mp4").write_bytes(b"existing video")
    monkeypatch.setattr("tv_runner.MINIMUM_FILE_SIZE", 0)

    TvRunner().handleDirs(root)

    assert video.read_bytes() == b"video"
    assert sidecar.read_bytes() == b"subtitle"
    assert (root / "One.mp4").read_bytes() == b"existing video"


def test_ambiguous_generic_sidecar_stays_unclaimed(tmp_path):
    one = tmp_path / "One.mp4"
    two = tmp_path / "Two.mp4"
    generic = tmp_path / "English.srt"
    one.touch()
    two.touch()
    generic.write_text("subtitle")

    assert generic not in utils.matching_subtitle_files(one, [one, two])
    assert generic not in utils.matching_subtitle_files(two, [one, two])


def test_longest_video_owner_and_encoded_alias(tmp_path):
    short = tmp_path / "Show.S01E01.mp4"
    long = tmp_path / "Show.S01E01.Special.mp4"
    sub = tmp_path / "Show.S01E01.Special.en.vtt"
    short.touch()
    long.touch()
    sub.touch()
    assert utils.matching_subtitle_files(short, [short, long]) == []
    assert utils.matching_subtitle_files(long, [short, long]) == [sub]

    encoded = tmp_path / f"Show.S01E01.Special.{MEDIAVIEWER_SUFFIX}"
    encoded.touch()
    assert utils.matching_subtitle_files(long, [long, encoded]) == [sub]


@pytest.mark.parametrize("encoded_suffix", [MEDIAVIEWER_SUFFIX, "custom-encoded.mp4"])
def test_default_inventory_normalizes_encoded_video_owners(
    tmp_path, monkeypatch, encoded_suffix
):
    monkeypatch.setattr(utils, "MEDIAVIEWER_SUFFIX", encoded_suffix)
    short = tmp_path / f"Show.S01E01.{encoded_suffix}"
    long = tmp_path / f"Show.S01E01.Special.{encoded_suffix}"
    sub = tmp_path / "Show.S01E01.Special.en.vtt"
    short.touch()
    long.touch()
    sub.touch()

    assert utils.matching_subtitle_files(short) == []
    assert utils.matching_subtitle_files(long) == [sub]


def test_upload_without_inventory_rejects_more_specific_video_tracks(
    tmp_path, monkeypatch
):
    short = tmp_path / "Show.S01E01.mp4"
    long = tmp_path / "Show.S01E01.Special.mp4"
    short.touch()
    long.touch()
    specific_tracks = [
        tmp_path / "Show.S01E01.Special.en.vtt",
        tmp_path / "Show.S01E01.Special.vtt",
    ]
    for track in specific_tracks:
        track.touch()
    uploads = []

    class Client:
        def upload_file(self, *args):
            uploads.append(args)

    monkeypatch.setattr(utils.b2, "get_b2_client", lambda: Client())
    monkeypatch.setattr(utils, "B2_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(utils, "B2_NAME_PREFIX", "test/")

    assert utils.upload_subtitle_files(short, tmp_path) == []
    assert uploads == []


def test_conversion_then_uploads_one_track_and_preserves_existing_index(
    tmp_path, monkeypatch
):
    source = tmp_path / "Episode.mp4"
    source.touch()
    srt = tmp_path / "Episode.en.srt"
    srt.write_text("new subtitle")
    existing = tmp_path / f"Episode.mp4.{MEDIAVIEWER_SUFFIX}-0.vtt"
    existing.write_text("existing subtitle")
    conversions = []

    def convert_srt(path):
        output = Path(path).with_suffix(".vtt")
        output.write_text("converted subtitle")
        conversions.append(output)
        return output

    uploads = []

    class Client:
        def upload_file(self, path, bucket, key):
            uploads.append((Path(path).read_text(), bucket, key))

    monkeypatch.setattr(convert, "_convertSrtToVtt", convert_srt)
    monkeypatch.setattr(utils.b2, "get_b2_client", lambda: Client())
    monkeypatch.setattr(utils, "B2_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(utils, "B2_NAME_PREFIX", "test/")

    convert._handleSubtitles(source, source, None)
    names = utils.upload_subtitle_files(source, tmp_path)

    assert len(names) == len(uploads) == 2
    assert sorted(upload[0] for upload in uploads) == [
        "converted subtitle",
        "existing subtitle",
    ]
    assert not srt.exists()
    assert existing.read_text() == "existing subtitle"
    assert len(conversions) == 1


def test_failed_conversion_retains_original_srt(tmp_path, monkeypatch):
    source = tmp_path / "Episode.mp4"
    source.touch()
    srt = tmp_path / "Episode.en.srt"
    srt.write_text("keep me")

    def fail_conversion(path):
        raise RuntimeError("conversion failed")

    monkeypatch.setattr(convert, "_convertSrtToVtt", fail_conversion)
    with pytest.raises(RuntimeError, match="conversion failed"):
        convert._handleSubtitles(source, source, None)
    assert srt.read_text() == "keep me"


def test_missing_conversion_output_retains_original_srt(tmp_path, monkeypatch):
    source = tmp_path / "Episode.mp4"
    source.touch()
    srt = tmp_path / "Episode.en.srt"
    srt.write_text("keep me")

    monkeypatch.setattr(
        convert, "_convertSrtToVtt", lambda path: Path(path).with_suffix(".vtt")
    )
    with pytest.raises(convert.EncoderException, match="did not create destination"):
        convert._handleSubtitles(source, source, None)
    assert srt.read_text() == "keep me"


def test_generic_vtt_preferred_over_srt(tmp_path):
    video = tmp_path / "Episode.mp4"
    srt = tmp_path / "English.srt"
    vtt = tmp_path / "English.vtt"
    video.touch()
    srt.touch()
    vtt.touch()

    assert utils.matching_subtitle_files(video) == [vtt]


def test_conversion_allocates_unused_index_without_clobbering(tmp_path, monkeypatch):
    source = tmp_path / "Episode.mp4"
    source.touch()
    srt = tmp_path / "Episode.en.srt"
    srt.write_text("new subtitle")
    existing = tmp_path / f"Episode.mp4.{MEDIAVIEWER_SUFFIX}-0.vtt"
    existing.write_text("old subtitle")

    def convert_srt(path):
        output = Path(path).with_suffix(".vtt")
        output.write_text("converted")
        return output

    monkeypatch.setattr(convert, "_convertSrtToVtt", convert_srt)
    convert._handleSubtitles(source, source, None)

    assert existing.read_text() == "old subtitle"
    assert (
        tmp_path / f"Episode.mp4.{MEDIAVIEWER_SUFFIX}-1.vtt"
    ).read_text() == "converted"


def test_extraction_retry_skips_existing_index(tmp_path, monkeypatch):
    source = tmp_path / "Episode.mp4"
    source.touch()
    existing = tmp_path / f"Episode.mp4.{MEDIAVIEWER_SUFFIX}-0.vtt"
    existing.write_text("old subtitle")

    def extract(source, stream, srt_path):
        Path(srt_path).write_text("extracted")

    def convert_srt(path):
        output = Path(path).with_suffix(".vtt")
        output.write_text("extracted vtt")
        return output

    monkeypatch.setattr(convert, "_extractSubtitleFromVideo", extract)
    monkeypatch.setattr(convert, "_convertSrtToVtt", convert_srt)
    convert._handleSubtitles(source, source, match("(1):(2)", "1:2"))

    assert existing.read_text() == "old subtitle"
    assert (
        tmp_path / f"Episode.mp4.{MEDIAVIEWER_SUFFIX}-1.vtt"
    ).read_text() == "extracted vtt"
