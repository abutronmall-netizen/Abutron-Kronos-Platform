from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes


class DPAPIError(RuntimeError):
    pass


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _require_windows():
    if os.name != "nt":
        raise DPAPIError("Windows DPAPI is only available on Windows")


def protect_for_current_user(value: str) -> str:
    _require_windows()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    source, source_buffer = _blob(value.encode("utf-8"))
    target = DATA_BLOB()
    ok = crypt32.CryptProtectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target))
    _ = source_buffer
    if not ok:
        raise DPAPIError("CryptProtectData failed")
    try:
        raw = ctypes.string_at(target.pbData, target.cbData)
        return base64.urlsafe_b64encode(raw).decode("ascii")
    finally:
        kernel32.LocalFree(target.pbData)


def unprotect_for_current_user(token: str) -> str:
    _require_windows()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    source, source_buffer = _blob(raw)
    target = DATA_BLOB()
    ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target))
    _ = source_buffer
    if not ok:
        raise DPAPIError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(target.pbData, target.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(target.pbData)
