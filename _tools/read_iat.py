# -*- coding: utf-8 -*-
"""Read IAT slot used by dispatcher to fetch function_record."""

import ctypes
import subprocess
from ctypes import wintypes

SLOT = 0x14189FAAD + 0xC18340B
print("IAT slot:", hex(SLOT))

pids = [int(x) for x in subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process -Name ZBrush -ErrorAction SilentlyContinue).Id"],
    capture_output=True, text=True).stdout.split() if x.strip()]
print("pids:", pids)
if not pids:
    raise SystemExit

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

h = k32.OpenProcess(0x0410, False, pids[0])
data = ctypes.create_string_buffer(8)
got = ctypes.c_size_t()
ok = k32.ReadProcessMemory(h, SLOT, data, 8, ctypes.byref(got))
print("read:", ok, data.raw.hex())
if ok:
    import struct
    print("target:", hex(struct.unpack("<Q", data.raw)[0]))
