import logging

import pytest
import requests

import b2
import utils


def test_multipart_logs_progress_only_after_successful_part(mocker, tmp_path, caplog):
    path = tmp_path / "large.bin"
    path.write_bytes(b"12345")
    mocker.patch.object(b2, "LARGE_FILE_PART_SIZE", 2)
    start_response = mocker.Mock()
    start_response.json.return_value = {"fileId": "file-id"}
    part_responses = [mocker.Mock(), mocker.Mock(), mocker.Mock()]
    part_responses[1].raise_for_status.side_effect = requests.HTTPError("upload failed")
    mocker.patch.object(
        b2.requests, "post", side_effect=[start_response, *part_responses]
    )
    part_url_response = mocker.Mock()
    part_url_response.json.return_value = {
        "uploadUrl": "https://upload.example/part",
        "authorizationToken": "secret",
    }
    mocker.patch.object(b2.requests, "get", return_value=part_url_response)
    client = b2.B2Client("id", "key")
    caplog.set_level(logging.INFO, logger="b2")

    with pytest.raises(requests.HTTPError):
        client._upload_large_file(
            path,
            "bucket-id",
            "opaque-key",
            {"apiUrl": "https://api.example", "authorizationToken": "secret"},
        )

    progress = [
        record.getMessage()
        for record in caplog.records
        if "Multipart part" in record.getMessage()
    ]
    assert any(
        "1/3" in message and "2/5 bytes" in message and "40.0%" in message
        for message in progress
    )
    assert not any("2/3" in message for message in progress)
    assert not any(
        "completed" in record.getMessage().lower() for record in caplog.records
    )


def test_api_logs_sanitized_endpoint_and_no_payload(mocker, caplog):
    response = mocker.Mock(status_code=200)
    response.raise_for_status.return_value = None
    mocker.patch.object(utils.requests, "post", return_value=response)
    mocker.patch.object(utils, "_external_request_cooldown", return_value=0)
    caplog.set_level(logging.DEBUG, logger="utils")
    secret = "payload-secret"

    utils._make_request(
        "POST",
        "https://user:password@example.test/path?token=query-secret#fragment",
        values={"private": secret},
    )

    logs = " ".join(record.getMessage() for record in caplog.records)
    assert "https://example.test/path" in logs
    assert "query-secret" not in logs
    assert "password" not in logs
    assert "fragment" not in logs
    assert secret not in logs
    assert "200" in logs


def test_api_failure_does_not_log_url_or_exception_secrets(mocker, caplog):
    error = requests.HTTPError(
        "https://user:password@example.test/path?token=exception-secret"
    )
    error.response = mocker.Mock(status_code=503)
    mocker.patch.object(utils.requests, "get", side_effect=error)
    caplog.set_level(logging.WARNING, logger="utils")

    with pytest.raises(requests.HTTPError):
        utils._make_request(
            "GET", "https://user:password@example.test/path?token=query-secret"
        )

    logs = " ".join(record.getMessage() for record in caplog.records)
    assert "https://example.test/path" in logs
    assert "503" in logs
    assert "password" not in logs
    assert "query-secret" not in logs
    assert "exception-secret" not in logs


@pytest.mark.parametrize("fail_upload", [False, True])
def test_public_b2_upload_logs_identity_and_only_success_completion(
    mocker, tmp_path, caplog, fail_upload
):
    local_path = tmp_path / "movie.mp4"
    local_path.write_bytes(b"1234567")
    client = b2.B2Client("id", "key")
    mocker.patch.object(client, "_authorize", return_value={"buckets": {}})
    mocker.patch.object(client, "_bucket_id", return_value="bucket-id")
    if fail_upload:
        mocker.patch.object(
            client, "_upload_single_file", side_effect=RuntimeError("upload failed")
        )
    else:
        mocker.patch.object(client, "_upload_single_file")
    caplog.set_level(logging.INFO, logger="b2")

    if fail_upload:
        with pytest.raises(RuntimeError):
            client.upload_file(local_path, "media", "movies/movie.mp4")
    else:
        client.upload_file(local_path, "media", "movies/movie.mp4")

    logs = " ".join(record.getMessage() for record in caplog.records)
    assert str(local_path) in logs
    assert "b2://media/movies/movie.mp4" in logs
    assert "7 bytes" in logs
    assert "B2 upload started" in logs
    assert ("B2 upload completed" in logs) is (not fail_upload)
    if not fail_upload:
        assert "seconds" in logs
        assert "bytes/s" in logs


@pytest.mark.parametrize("large", [False, True])
@pytest.mark.parametrize("success_on", [1, 2, 3])
def test_b2_upload_retries_http_errors_until_success(
    mocker, tmp_path, large, success_on
):
    path = tmp_path / "upload.bin"
    path.write_bytes(b"data")
    client = b2.B2Client("id", "key")
    mocker.patch.object(client, "_authorize", return_value={"buckets": {}})
    mocker.patch.object(client, "_bucket_id", return_value="bucket-id")
    upload = mocker.patch.object(
        client,
        "_upload_large_file" if large else "_upload_single_file",
        side_effect=[
            *[requests.HTTPError(f"failure {n}") for n in range(success_on - 1)],
            None,
        ],
    )
    mocker.patch.object(b2, "MAX_SINGLE_UPLOAD_SIZE", 0 if large else 100)

    client.upload_file(path, "bucket", "opaque/key")

    assert upload.call_count == success_on
    assert all(
        call.args[:3] == (path, "bucket-id", "opaque/key")
        for call in upload.call_args_list
    )


@pytest.mark.parametrize("large", [False, True])
def test_b2_upload_retries_three_times_then_reraises_final_http_error(
    mocker, tmp_path, large
):
    path = tmp_path / "upload.bin"
    path.write_bytes(b"data")
    client = b2.B2Client("id", "key")
    mocker.patch.object(client, "_authorize", return_value={"buckets": {}})
    mocker.patch.object(client, "_bucket_id", return_value="bucket-id")
    errors = [requests.HTTPError(f"failure {n}") for n in range(3)]
    upload = mocker.patch.object(
        client,
        "_upload_large_file" if large else "_upload_single_file",
        side_effect=errors,
    )
    mocker.patch.object(b2, "MAX_SINGLE_UPLOAD_SIZE", 0 if large else 100)

    with pytest.raises(requests.HTTPError) as raised:
        client.upload_file(path, "bucket", "opaque/key")

    assert raised.value is errors[-1]
    assert upload.call_count == 3


def test_single_upload_retry_replays_file_from_start(mocker, tmp_path):
    path = tmp_path / "upload.bin"
    path.write_bytes(b"payload")
    client = b2.B2Client("id", "key")
    mocker.patch.object(
        client,
        "_authorize",
        return_value={"buckets": {}, "authorizationToken": "token"},
    )
    mocker.patch.object(client, "_bucket_id", return_value="bucket-id")
    mocker.patch.object(
        client,
        "_get_upload_url",
        return_value={
            "uploadUrl": "https://upload.example/file",
            "authorizationToken": "token",
        },
    )
    observed = []

    def post(_url, data, **_kwargs):
        observed.append(data.read())
        response = mocker.Mock()
        if len(observed) == 1:
            response.raise_for_status.side_effect = requests.HTTPError("failed")
        return response

    mocker.patch.object(b2.requests, "post", side_effect=post)

    client.upload_file(path, "bucket", "key")

    assert observed == [b"payload", b"payload"]


def test_inference_transport_failure_propagates(mocker, caplog):
    error = requests.ConnectionError("network unavailable")
    mocker.patch.object(utils.requests, "get", side_effect=error)
    caplog.set_level(logging.WARNING, logger="utils")

    with pytest.raises(requests.ConnectionError) as raised:
        utils.get_media_path_by_filename("episode-title")

    assert raised.value is error
    logs = " ".join(record.getMessage() for record in caplog.records)
    assert "GET" in logs
    assert "ConnectionError" in logs
    assert "network unavailable" not in logs


def test_inference_failure_logs_filename_and_status_not_body(mocker, caplog):
    response = mocker.Mock(status_code=503)
    response.text = "response-body-secret"
    response.raise_for_status.side_effect = requests.HTTPError(
        "request failed", response=response
    )
    mocker.patch.object(utils.requests, "get", return_value=response)
    caplog.set_level(logging.WARNING, logger="utils")

    assert utils.get_media_path_by_filename("episode-title") is None

    logs = " ".join(record.getMessage() for record in caplog.records)
    assert "episode-title" in logs
    assert "503" in logs
    assert "response-body-secret" not in logs


def test_subtitle_progress_count_completion_only_after_all_uploads(
    mocker, tmp_path, caplog
):
    video = tmp_path / "episode.mp4"
    video.write_bytes(b"video")
    for index in (1, 2):
        (tmp_path / f"episode-{index}.vtt").write_bytes(b"subtitle")
    upload_client = mocker.patch("utils.b2.get_b2_client").return_value
    upload_client.upload_file.side_effect = [None, RuntimeError("upload failed")]
    caplog.set_level(logging.INFO, logger="utils")

    with pytest.raises(RuntimeError):
        utils.upload_subtitle_files(video, tmp_path, "bucket", "prefix/")

    logs = [record.getMessage() for record in caplog.records]
    assert any("2 subtitle" in message for message in logs)
    assert any("[1/2]" in message for message in logs)
    assert any("[2/2]" in message for message in logs)
    assert any(str(video) in message for message in logs)
    assert any("b2://bucket/prefix/" in message for message in logs)
    assert any("episode-1.vtt" in message for message in logs)
    assert not any("Uploaded 2 subtitle" in message for message in logs)
