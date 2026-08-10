# -*- coding: utf-8 -*-
import ctypes
import struct
import subprocess
from ctypes import wintypes

STUB = 0x14D00000

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
for off, label in ((0x60, "real_fn"), (0x70, "counter")):
    data = ctypes.create_string_buffer(8)
    got = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(h, STUB + off, data, 8, ctypes.byref(got))
    v = struct.unpack("<Q", data.raw)[0] if ok else None
    print("%s @ %#x: ok=%s value=%s" % (label, STUB + off, ok,
                                        hex(v) if v else None))
