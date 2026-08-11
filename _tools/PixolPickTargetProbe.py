# -*- coding: utf-8 -*-
"""One-shot ZBrush 2026.1.1 PixolPick target capture.

The probe temporarily instruments two indirect calls in the shared Python
command dispatcher, invokes pixol_pick once, restores the original bytes, and
writes the captured native targets to ``%TEMP%\\pixol_pick_target_probe.log``.
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes


LOG_PATH = os.path.join(
    os.environ.get("TEMP", os.path.dirname(__file__)),
    "lightbox_press_target_probe.log",
)

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


SITES = (
    {
        "name": "record_call",
        "rva": 0x18A053F,
        "continue_rva": 0x18A0552,
        "original": bytes.fromhex(
            "498b4530"
            "488d9424c0010000"
            "488d4c2470"
            "ffd0"
        ),
        "prefix": bytes.fromhex(
            "498b4530"
            "488d9424c0010000"
            "488d4c2470"
        ),
        "record_instruction": b"\x48\x89\x05",  # mov [rip+disp32], rax
        "call_instruction": b"\xFF\xD0",         # call rax
    },
    {
        "name": "object_call",
        "rva": 0x18A0643,
        "continue_rva": 0x18A0655,
        "original": bytes.fromhex(
            "488b03"
            "4c8b4030"
            "488bd3"
            "488d4c2470"
            "41ffd0"
        ),
        "prefix": bytes.fromhex(
            "488b03"
            "4c8b4030"
            "488bd3"
            "488d4c2470"
        ),
        "record_instruction": b"\x4C\x89\x05",  # mov [rip+disp32], r8
        "call_instruction": b"\x41\xFF\xD0",     # call r8
    },
)


def _log(message: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as stream:
        stream.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))


def _write_code(address: int, data: bytes) -> bool:
    old_protection = wintypes.DWORD()
    if not kernel32.VirtualProtect(
        address,
        len(data),
        PAGE_READWRITE,
        ctypes.byref(old_protection),
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


def _build_stub(site: dict, stub_address: int, image_base: int) -> bytes:
    data_offset = 0x80
    code = bytearray(site["prefix"])
    next_ip = stub_address + len(code) + 7
    displacement = (stub_address + data_offset) - next_ip
    code += site["record_instruction"] + struct.pack("<i", displacement)
    code += site["call_instruction"]
    continuation = image_base + site["continue_rva"]
    code += b"\x49\xBB" + struct.pack("<Q", continuation)  # mov r11, imm64
    code += b"\x41\xFF\xE3"                               # jmp r11
    if len(code) > data_offset:
        raise RuntimeError("stub overflow")
    code.extend(b"\x90" * (data_offset - len(code)))
    code.extend(struct.pack("<Q", 0))
    return bytes(code)


def _install_site(site: dict, image_base: int) -> dict:
    address = image_base + site["rva"]
    original = site["original"]
    actual = ctypes.string_at(address, len(original))
    if actual != original:
        raise RuntimeError(
            "%s signature mismatch: %s" % (site["name"], actual.hex())
        )

    stub_address = int(
        kernel32.VirtualAlloc(
            None,
            0x1000,
            MEM_COMMIT | MEM_RESERVE,
            PAGE_EXECUTE_READWRITE,
        )
        or 0
    )
    if not stub_address:
        raise OSError("VirtualAlloc failed")
    stub = _build_stub(site, stub_address, image_base)
    ctypes.memmove(stub_address, stub, len(stub))
    kernel32.FlushInstructionCache(
        kernel32.GetCurrentProcess(), stub_address, len(stub)
    )

    patch = b"\x49\xBB" + struct.pack("<Q", stub_address) + b"\x41\xFF\xE3"
    patch += b"\x90" * (len(original) - len(patch))
    if not _write_code(address, patch):
        raise OSError("%s patch failed" % site["name"])
    return {
        "site": site,
        "address": address,
        "stub": stub_address,
        "data": stub_address + 0x80,
    }


def _restore(installed: dict) -> None:
    site = installed["site"]
    if not _write_code(installed["address"], site["original"]):
        _log("CRITICAL restore failed for " + site["name"])


def main() -> None:
    with open(LOG_PATH, "w", encoding="utf-8") as stream:
        stream.write("=== PixolPick target probe ===\n")

    image_base = int(kernel32.GetModuleHandleW(None) or 0)
    if not image_base:
        _log("ERROR no image base")
        return
    _log("image_base=%#x" % image_base)

    installed = []
    value = None
    error = ""
    try:
        for site in SITES:
            item = _install_site(site, image_base)
            installed.append(item)
            _log("installed %s stub=%#x" % (site["name"], item["stub"]))

        import zbrush.commands as zbc

        zbc.press("Preferences:LightBox:LightBox")
        zbc.press("Preferences:LightBox:LightBox")
        value = 1.0
    except Exception as exception:
        error = repr(exception)
        _log("ERROR " + error)
    finally:
        for item in reversed(installed):
            _restore(item)

    for item in installed:
        target = ctypes.c_uint64.from_address(item["data"]).value
        _log("captured %s target=%#x" % (item["site"]["name"], target))
        if image_base <= target < image_base + 0xE000000:
            _log(
                "captured %s rva=%#x bytes=%s"
                % (
                    item["site"]["name"],
                    target - image_base,
                    ctypes.string_at(target, 128).hex(),
                )
            )
    _log("pixol_value=%r error=%s" % (value, error))

    try:
        import zbrush.commands as zbc

        zbc.set_notebar_text("LightBox press target probe complete: " + LOG_PATH)
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
