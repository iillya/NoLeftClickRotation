# -*- coding: utf-8 -*-
"""One-shot capture of the final PixolPick implementation target."""

import ctypes
import os
import struct
import time
from ctypes import wintypes


LOG_PATH = os.path.join(
    os.environ.get("TEMP", os.path.dirname(__file__)),
    "lightbox_callback_probe.log",
)

OUTER_RVA = 0x4CF545
ORIGINAL = bytes.fromhex("488bf84885c00f847602000033d2")
CONTINUE_RVA = OUTER_RVA + len(ORIGINAL)

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetCurrentProcess.restype = ctypes.c_void_p
kernel32.GetCurrentProcess.argtypes = []
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.FlushInstructionCache.restype = wintypes.BOOL
kernel32.FlushInstructionCache.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
]


def _log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as stream:
        stream.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))


def _write_code(address: int, data: bytes) -> bool:
    old_protection = wintypes.DWORD()
    if not kernel32.VirtualProtect(
        address, len(data), PAGE_READWRITE, ctypes.byref(old_protection)
    ):
        return False
    try:
        ctypes.memmove(address, data, len(data))
        kernel32.FlushInstructionCache(
            kernel32.GetCurrentProcess(), address, len(data)
        )
    finally:
        restored = wintypes.DWORD()
        kernel32.VirtualProtect(
            address,
            len(data),
            old_protection.value,
            ctypes.byref(restored),
        )
    return ctypes.string_at(address, len(data)) == data


def _build_stub(stub: int, image_base: int) -> bytes:
    data_offset = 0x80
    code = bytearray()

    # RAX is the resolved UI item returned by the path lookup.
    next_ip = stub + len(code) + 7
    code += b"\x48\x89\x05" + struct.pack(
        "<i", (stub + data_offset) - next_ip
    )

    # Replay through and including the original indirect call.
    code += ORIGINAL
    code += b"\x49\xBB" + struct.pack("<Q", image_base + CONTINUE_RVA)
    code += b"\x41\xFF\xE3"

    if len(code) > data_offset:
        raise RuntimeError("stub overflow")
    code.extend(b"\x90" * (data_offset - len(code)))
    code.extend(struct.pack("<Q", 0))
    return bytes(code)


def main() -> None:
    with open(LOG_PATH, "w", encoding="utf-8") as stream:
        stream.write("=== PixolPick inner target probe ===\n")

    image_base = int(kernel32.GetModuleHandleW(None) or 0)
    address = image_base + OUTER_RVA
    actual = ctypes.string_at(address, len(ORIGINAL))
    if actual != ORIGINAL:
        _log("ERROR signature mismatch: " + actual.hex())
        return

    stub = int(
        kernel32.VirtualAlloc(
            None,
            0x1000,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE,
        )
        or 0
    )
    if not stub:
        _log("ERROR VirtualAlloc failed")
        return
    stub_code = _build_stub(stub, image_base)
    ctypes.memmove(stub, stub_code, len(stub_code))
    kernel32.FlushInstructionCache(
        kernel32.GetCurrentProcess(), stub, len(stub_code)
    )

    patch = (
        b"\x49\xBB" + struct.pack("<Q", stub) + b"\x41\xFF\xE3"
        + b"\x90" * (len(ORIGINAL) - 13)
    )
    if len(patch) != len(ORIGINAL):
        _log("ERROR invalid patch length")
        return
    if not _write_code(address, patch):
        _log("ERROR install failed")
        return

    value = None
    error = ""
    try:
        import zbrush.commands as zbc

        zbc.press("Preferences:LightBox:LightBox")
        zbc.press("Preferences:LightBox:LightBox")
        value = 1.0
    except Exception as exception:
        error = repr(exception)
    finally:
        if not _write_code(address, ORIGINAL):
            _log("CRITICAL restore failed")

    target = ctypes.c_uint64.from_address(stub + 0x80).value
    _log("image_base=%#x" % image_base)
    _log("inner_target=%#x" % target)
    if image_base <= target < image_base + 0xE000000:
        _log("inner_rva=%#x" % (target - image_base))
        _log("inner_bytes=" + ctypes.string_at(target, 256).hex())
    elif target:
        _log("ui_item_bytes=" + ctypes.string_at(target, 512).hex())
        state = ctypes.c_uint64.from_address(target + 0xA8).value
        _log("ui_state=%#x" % state)
        if state:
            _log("ui_state_bytes=" + ctypes.string_at(state, 256).hex())
            callback = ctypes.c_uint64.from_address(state + 0xA8).value
            _log("ui_callback=%#x" % callback)
            if image_base <= callback < image_base + 0xE000000:
                _log("ui_callback_rva=%#x" % (callback - image_base))
    _log("pixol_value=%r error=%s" % (value, error))

    try:
        import zbrush.commands as zbc

        zbc.set_notebar_text("Pixol inner probe complete: " + LOG_PATH)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        try:
            _log("FATAL " + repr(exception))
        except Exception:
            pass
