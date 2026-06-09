from __future__ import annotations

import io
import tarfile
from unittest.mock import MagicMock, patch

import pytest

from letterforge.config import SandboxConfig
from letterforge.sandbox.executor import DockerSandbox, SandboxResult


@pytest.fixture
def mock_docker(monkeypatch):
    with patch("letterforge.sandbox.executor.DockerSandbox.__init__") as mock_init:
        mock_init.return_value = None
        yield mock_init


@pytest.fixture
def sandbox_config():
    return SandboxConfig(
        docker_image="letterforge-sandbox:latest",
        timeout_seconds=5,
        network_disabled=True,
        auto_build=False,
    )


def _make_tar_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name=f"outputs/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return buf.getvalue()


def test_put_files_creates_tar():
    config = SandboxConfig()
    sandbox = DockerSandbox.__new__(DockerSandbox)
    sandbox._config = config

    container = MagicMock()
    sandbox._put_files(container, "/workspace", {"test.py": b"print('hi')"})
    container.put_archive.assert_called_once()


def test_get_files_extracts_pngs():
    config = SandboxConfig()
    sandbox = DockerSandbox.__new__(DockerSandbox)
    sandbox._config = config

    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    tar_bytes = _make_tar_bytes({"upper_A.png": png_data, "lower_a.png": png_data})

    container = MagicMock()
    container.get_archive.return_value = (iter([tar_bytes]), {})

    result = sandbox._get_files(container, "/workspace/outputs")
    assert "upper_A.png" in result
    assert "lower_a.png" in result
    assert result["upper_A.png"] == png_data


def test_get_files_ignores_non_png():
    config = SandboxConfig()
    sandbox = DockerSandbox.__new__(DockerSandbox)
    sandbox._config = config

    tar_bytes = _make_tar_bytes({"upper_A.png": b"\x89PNG", "readme.txt": b"hello"})

    container = MagicMock()
    container.get_archive.return_value = (iter([tar_bytes]), {})

    result = sandbox._get_files(container, "/workspace/outputs")
    assert "upper_A.png" in result
    assert "readme.txt" not in result


def test_get_files_returns_empty_on_error():
    config = SandboxConfig()
    sandbox = DockerSandbox.__new__(DockerSandbox)
    sandbox._config = config

    container = MagicMock()
    container.get_archive.side_effect = Exception("not found")

    result = sandbox._get_files(container, "/workspace/outputs")
    assert result == {}
