import importlib.util
from pathlib import Path

import pytest

from autoopen import find_handler, autoopen, OpenHandler, NoCompressorError


@pytest.fixture
def test_path() -> Path:
    return Path(__file__).resolve().parent


def test_find_handler():
    handler = find_handler("foo.txt.gz")
    assert handler.description == "GZip"


@pytest.mark.parametrize("suffix", [".gz", ".bz2", ".xz", ".lzma", ""])
def test_read(test_path, suffix):
    with autoopen(test_path / ("hello.txt" + suffix), "rt") as f:
        text = f.read()
        assert text == "Hello World!\n"


@pytest.mark.skipif(
    importlib.util.find_spec("zstandard") is None, reason="requires zstandard from pypi"
)
def test_read_zstd(test_path):
    return test_read(test_path, ".zst")


def test_read_unavailable(test_path):
    OpenHandler(
        [".doesnotexist"], description="Not Existing format", module="doesnotexist"
    ).register()
    with pytest.raises(NoCompressorError):
        with autoopen(test_path / "hello.txt.doesnotexist", "rt") as f:
            return f.read()
