"""Windows DPAPI wrapper (ctypes only) for protecting small secrets at rest."""
import base64
import binascii
import sys


class SecretStoreError(OSError):
    """Protect/unprotect failed. The message never contains the plaintext."""


_UI_FORBIDDEN = 0x1


def _api():
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    pblob = ctypes.POINTER(DATA_BLOB)
    for fn in (crypt32.CryptProtectData, crypt32.CryptUnprotectData):
        fn.restype = wintypes.BOOL
    crypt32.CryptProtectData.argtypes = [
        pblob, wintypes.LPCWSTR, pblob, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, pblob]
    crypt32.CryptUnprotectData.argtypes = [
        pblob, ctypes.c_void_p, pblob, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, pblob]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    return ctypes, DATA_BLOB, crypt32, kernel32


def _run(protect: bool, data: bytes) -> bytes:
    if sys.platform != "win32":
        raise SecretStoreError("DPAPI is only available on Windows")
    try:
        ctypes, DATA_BLOB, crypt32, kernel32 = _api()
        buf = ctypes.create_string_buffer(data, len(data))
        inp = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        out = DATA_BLOB()
        fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        if protect:
            ok = fn(ctypes.byref(inp), None, None, None, None, _UI_FORBIDDEN, ctypes.byref(out))
        else:
            ok = fn(ctypes.byref(inp), None, None, None, None, _UI_FORBIDDEN, ctypes.byref(out))
        if not ok:
            raise SecretStoreError("DPAPI call failed")
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            kernel32.LocalFree(ctypes.cast(out.pbData, ctypes.c_void_p))
    except SecretStoreError:
        raise
    except Exception:
        raise SecretStoreError("DPAPI call failed") from None


def protect(text: str) -> str:
    if not isinstance(text, str):
        raise SecretStoreError("text must be a string")
    return base64.b64encode(_run(True, text.encode("utf-8"))).decode("ascii")


def unprotect(token: str) -> str:
    if not isinstance(token, str):
        raise SecretStoreError("token must be a string")
    try:
        blob = base64.b64decode(token.encode("ascii"), validate=True)
    except (binascii.Error, ValueError):
        raise SecretStoreError("token is not valid base64") from None
    try:
        return _run(False, blob).decode("utf-8")
    except UnicodeDecodeError:
        raise SecretStoreError("decrypted data is not valid text") from None
