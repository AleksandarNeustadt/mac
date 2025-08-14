# ========================================================================
# File:       system/helpers/core_helper.py
# Purpose:    Bezbedni pozivi + brzi/atomski I/O helperi
# Author:     Aleksandar Popovic
# Created:    2025-08-07
# Updated:    2025-08-13
# ========================================================================

from __future__ import annotations
import os, tempfile, io
from typing import Any, Callable
from contextlib import contextmanager

def safe_call(func: Callable, *args, **kwargs):
    """Poziva funkciju i prepušta izuzetke višem sloju; zadržavamo postojeći ugovor."""
    return func(*args, **kwargs)

def _fsync_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path)) or "."
    try:
        fd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        # Na nekim FS (npr. mrežni) fsync direktorijuma nije podržan — ignoriši.
        pass

def atomic_write(path: str, data: str | bytes, *, text: bool = True, encoding: str = "utf-8") -> None:
    """
    Atomičan upis: temp fajl -> fsync -> os.replace -> fsync dir.
    Osetno smanjuje šansu za korupciju + daje stabilniji throughput kod bursts.
    """
    folder = os.path.dirname(path) or "."
    os.makedirs(folder, exist_ok=True)
    mode = "w" if text else "wb"

    with tempfile.NamedTemporaryFile(mode=mode, delete=False, dir=folder) as tf:
        tmp = tf.name
        if text:
            tf.write(data if isinstance(data, str) else data.decode(encoding))
        else:
            tf.write(data if isinstance(data, (bytes, bytearray)) else bytes(data))
        tf.flush()
        os.fsync(tf.fileno())

    os.replace(tmp, path)
    _fsync_dir(path)

@contextmanager
def savepoint(stack, adapter):
    """
    Generički savepoint helper za drajvere koji podržavaju ugnježdene transakcije.
    adapter mora da ima .begin(name), .release(name), .rollback_to(name)
    """
    name = f"sp_{len(stack)+1}"
    stack.append(name)
    adapter.begin(name)
    try:
        yield
        adapter.release(name)
    except Exception:
        adapter.rollback_to(name)
        raise
    finally:
        stack.pop()
