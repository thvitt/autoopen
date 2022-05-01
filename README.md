# autoopen

_autoopen_ is a small drop-in replacement for the most common use cases of Python’s built-in open() function that will automatically handle compressed files based on the filename.

## Usage

For example:

```python
from autoopen import autoopen

filename = "example.txt.xz"
with autoopen(filename, "rt", encoding="utf-8") as file:
    contents = file.read()
```

`autoopen` will check the given filename’s last suffix. If it indicates one of the supported compressors, the corresponding compressor or decompressor will be used, otherwise it falls back to built-in `open`. 

Support for .gz, .bz2, .xz, .lzma, and .zst/.zstd is built-in (the latter requires the [python-zstandard](https://pypi.org/project/zstandard/) package). The special filename `-` indicates reading from stdin or writing to stdout.