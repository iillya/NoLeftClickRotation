# -*- coding: utf-8 -*-
"""Find which module contains given address in the ZBrush process."""

import ctypes
import subprocess
from ctypes import wintypes

addrs = [0x7FF8DAD69DB0, 0x7FF8DAD76E80, 0x7FF8DACF8B90,
         0x7FF8DACCED80, 0x7FF8DAD6F710, 0x7FF8DAE1A148,
         0x7FF8DAD41B20, 0x7FF8DACBF040]

pids = [int(x) for x in subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "(Get-Process -Name ZBrush -ErrorAction SilentlyContinue).Id"],
    capture_output=True, text=True).stdout.split() if x.strip()]
print("pids:", pids)
if not pids:
    raise SystemExit

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
ps = ctypes.WinDLL("psapi")
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

class MODULEINFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", wintypes.LPVOID), ("SizeOfImage", wintypes.DWORD),
                ("EntryPoint", wintypes.LPVOID)]

ps.EnumProcessModulesEx.restype = wintypes.BOOL
ps.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE),
                                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
ps.GetModuleBaseNameW.restype = wintypes.DWORD
ps.GetModuleBaseNameW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
ps.GetModuleInformation.restype = wintypes.BOOL
ps.GetModuleInformation.argtypes = [wintypes.HANDLE, wintypes.HMODULE, ctypes.POINTER(MODULEINFO), wintypes.DWORD]
ps.GetModuleFileNameExW.restype = wintypes.DWORD
ps.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]

h = k32.OpenProcess(0x0410, False, pids[0])
buf = (wintypes.HMODULE * 4096)()
needed = wintypes.DWORD()
ps.EnumProcessModulesEx(h, buf, ctypes.sizeof(buf), ctypes.byref(needed), 0x03)
cnt = needed.value // ctypes.sizeof(wintypes.HMODULE)
print("modules:", cnt)
for i in range(cnt):
    nm = ctypes.create_unicode_buffer(260)
    ps.GetModuleBaseNameW(h, buf[i], nm, 260)
    mi = MODULEINFO()
    ps.GetModuleInformation(h, buf[i], ctypes.byref(mi), ctypes.sizeof(mi))
    base = int(mi.lpBaseOfDll)
    size = int(mi.SizeOfImage)
    for addr in addrs:
        if base <= addr < base + size:
            print("FOUND %#x: %s base=%#x size=%#x off=%#x"
                  % (addr, nm.value, base, size, addr - base))
            p = ctypes.create_unicode_buffer(1024)
            ps.GetModuleFileNameExW(h, buf[i], p, 1024)
            print("   path:", p.value)
