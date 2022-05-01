"""
autoopen is a small tool to transparently open files that are compressed using one of the common
one-file compression formats (like gzip, bzip2, xz) for the most common use cases.

Tool developers can write something like:

```
from autoopen import autoopen
filename = sys.argv[1]
with autoopen(filename, 'wt') as f:
    f.write('Hello world!')
```

If the user calls the tool using 'hello.txt', the file is written as a plain text file, with
'hello.txt.gz' it is GZip compressed and when using the special string '-', the data is written
to stdout.

## Advanced Usage

autoopen will look up the last suffix of the given filename in the `open_handlers` dictionary.
Each entry of that dictionary maps to a list of OpenHandler objects. autoopen takes the first
handler that says it is supported (i.e., the corresponding compressor module can be imported)
and calls it with its own arguments, returning the results.

Use `find_handler(filename)` to find the appropriate handler manually.



"""
import os
import sys
from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass
from functools import wraps
from importlib import import_module
from lzma import FORMAT_ALONE
from os import PathLike
from pathlib import Path
from typing import List, Optional, Callable

__all__ = ['autoopen']

open_handlers: dict[str, list['OpenHandler']] = defaultdict(list)


class NoCompressorError(IOError):
    ...


def find_handler(filename, checked=True):
    if filename == '-':
        candidates = open_handlers['-']
    else:
        path = Path(filename)
        last_suffix = path.suffixes[-1] if path.suffixes else None
        candidates = open_handlers[last_suffix]
    if candidates:
        for candidate in candidates:
            if candidate.is_supported():
                return candidate
        if checked:  # candidates, but none works
            raise NoCompressorError(
                    f"The file {filename} is compressed, but no matching compressor is available. Failed to import:\n" +
                    "\n".join(f' - {c.module} for {c.description}' for c in candidates)
            )
        else:
            return None
    else:
        return open_handlers[None][0]  # handler using default open function


def autoopen(file, mode='rt', encoding=None, errors=None, newline=None):
    """
    Opens a file, transparently (de-)compressing it by filename.

    This function checks the given file name's last suffix whether it belongs to a known single-file compression format.
    GIf so, it tries to use that compression library to open the file and returns the result. Otherwise, it simply calls
    `open()`.

    If file is the special string `-`, it will return stdin or stdout, depending on the mode.
    """
    handler = find_handler(file)
    return handler(os.fspath(file), mode=mode, encoding=encoding, errors=errors, newline=newline)


def openhandler(*extensions: List[str], description: Optional[str] = None, module: Optional[str] = None):
    """
    Decorator that registers a function as an open function for the given extensions.

    Args:
        *extensions:
        description:
        module:

    Returns:

    """

    def create_handler(f):
        handler = OpenHandler(extensions, description=description, module=module, open_function=f)
        handler.register()
        return handler

    return create_handler


@dataclass
class OpenHandler:
    """
    Base implementation of an registerable open handler.

    Attributes:
        suffixes: The file suffixes this handler will accept, e.g. `['.gz']
        description: A human-readable description
        module: Optional name of a module that is required for the handler to work
        open_function: An implementation of open that works like builtins.open()
    """
    suffixes: List[str]
    description: Optional[str] = None
    module: Optional[str] = None
    open_function: Optional[Callable] = None

    def register(self):
        for suffix in self.suffixes:
            open_handlers[suffix].append(self)

    def load_module(self):
        if self.module is not None:
            return import_module(self.module)
        else:
            return None

    def is_supported(self) -> bool:
        if self.module is None:
            return True
        else:
            try:
                self.load_module()
                return True
            except ImportError:
                return False

    def __call__(self, file, mode='rt', encoding=None, errors=None, newline=None):
        if self.open_function is None:
            if self.module is not None:
                module = self.load_module()
                self.open_function = module.open
            else:
                raise NotImplementedError(
                        f"Neither open implementation nor module with open function provided. This is a bug.")
        return self.open_function(file, mode=mode, encoding=encoding, errors=errors, newline=newline)


# Now, let's define and register some default handlers. These are from the standard library:

OpenHandler(['.gz'], description='GZip', module='gzip').register()
OpenHandler(['.bz2'], description='BZip2', module='bz2').register()
OpenHandler(['.xz'], description='LZMA files (.xz format)', module='lzma').register()
OpenHandler([None], description='uncompressed files', open_function=open).register()


@openhandler('.lzma', description='LZMA files (deprecated .lzma format', module='lzma')
def open_xz(filename, mode='rt', **kwargs):
    import lzma
    return lzma.open(filename, mode, format=FORMAT_ALONE, **kwargs)


# Here is our special stdin/out handler. TODO text/binary handling?
@openhandler('-', description='Use - to use stdin/stdout')
def open_stdinout(filename, mode='rt', **kwargs):
    if 'r' in mode:
        return nullcontext(sys.stdin)
    else:
        return nullcontext(sys.stdout)


# The zstandard handler will only work if the corresponding library is present.
OpenHandler(['.zst', '.zstd'], description='ZStandard', module='zstandard').register()
