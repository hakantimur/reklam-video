"""SSRF guard unit tests for app.providers.network.is_safe_public_url (spec §9.4)."""

from app.providers.network import is_safe_public_url


def test_rejects_file_scheme():
    assert is_safe_public_url("file:///etc/passwd") is False


def test_rejects_localhost_hostname():
    assert is_safe_public_url("http://localhost:8000/video.mp4") is False
    assert is_safe_public_url("https://localhost/video.mp4") is False


def test_rejects_loopback_ip_literal():
    assert is_safe_public_url("http://127.0.0.1/video.mp4") is False
    assert is_safe_public_url("http://127.0.0.1:9000/x") is False


def test_rejects_rfc1918_private_ranges():
    assert is_safe_public_url("http://10.0.0.5/x") is False
    assert is_safe_public_url("http://172.16.0.5/x") is False
    assert is_safe_public_url("http://192.168.1.5/x") is False


def test_rejects_link_local_cloud_metadata_ip():
    # 169.254.169.254 is the classic cloud-provider metadata SSRF target.
    assert is_safe_public_url("http://169.254.169.254/latest/meta-data") is False


def test_rejects_unspecified_and_multicast():
    assert is_safe_public_url("http://0.0.0.0/x") is False
    assert is_safe_public_url("http://224.0.0.1/x") is False


def test_rejects_non_http_schemes():
    assert is_safe_public_url("ftp://8.8.8.8/x") is False
    assert is_safe_public_url("data:text/plain;base64,aGk=") is False


def test_accepts_public_ip_literal_https():
    assert is_safe_public_url("https://8.8.8.8/video.mp4") is True


def test_accepts_public_ip_literal_http():
    assert is_safe_public_url("http://1.1.1.1/video.mp4") is True


def test_rejects_url_missing_hostname():
    assert is_safe_public_url("http:///no-host") is False
