# -*- coding: utf-8 -*-
"""Scan process memory for qwords pointing to the 'pixol_pick' name string.

pybind11 stores each function's record on the heap at runtime; the record
contains `name` (pointer to .rdata string) and the real function. We find
those records by scanning committed readable pages for the name pointer,
then dump nearby qwords that point into the ZBrush code section.
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_scan.log")

STR_VA = 0x14DAD8EC0          # RVA 0xDAD8EC0 + image base 0x140000000
CODE_LO = 0x140000000
CODE_HI = 0x160000000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


kernel32.VirtualQuery.restype = ctypes.c_size_t
kernel32.VirtualQuery.argtypes = [ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                                  ctypes.c_size_t]

MEM_COMMIT = 0x1000
PAGE_READABLE = 0x04 | 0x08 | 0x10 | 0x20 | 0x40 | 0x80


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def scan():
    addr = 0
    hits = []
    while addr < 0x7FFFFFFFFFFF:
        mbi = MEMORY_BASIC_INFORMATION()
        n = kernel32.VirtualQuery(ctypes.c_void_p(addr), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi))
        if not n:
            break
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if (mbi.State == MEM_COMMIT and mbi.Protect & PAGE_READABLE
                and not (mbi.Protect & 0x100) and size > 0):
            try:
                data = ctypes.string_at(base, size)
            except Exception:
                data = None
            if data:
                # find qwords == STR_VA
                for off in range(0, len(data) - 7, 8):
                    if struct.unpack_from("<Q", data, off)[0] == STR_VA:
                        hits.append(base + off)
        addr = base + size
    return hits


def main() -> None:
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr scan record ===\n")
    except Exception:
        pass
    _dlog("main start")
    try:
        hits = scan()
        _dlog("name-ptr hits: %d" % len(hits))
        for h in hits[:40]:
            _dlog("hit at %#x" % h)
            rec = h - 0x28
            try:
                blob0 = ctypes.string_at(rec, 0x400)
            except Exception:
                blob0 = b""
            for off in range(0, len(blob0) - 7, 8):
                v = struct.unpack_from("<Q", blob0, off)[0]
                tag = "CODE" if CODE_LO + 0x1000 <= v < CODE_HI else ""
                _dlog("  rec+%#x = %#x %s" % (off, v, tag))
                # follow heap pointers (depth 1) for code ptrs inside
                if 0x10000 <= v < 0x7FFFFFFFFFFF and not tag and v != STR_VA:
                    try:
                        inner = ctypes.string_at(v, 0x80)
                    except Exception:
                        continue
                    codes = []
                    for i in range(0, len(inner) - 7, 8):
                        iv = struct.unpack_from("<Q", inner, i)[0]
                        if CODE_LO + 0x1000 <= iv < CODE_HI:
                            codes.append((i, iv))
                    if codes:
                        _dlog("    rec+%#x -> %#x inner codes: %s"
                              % (off, v, ",".join("%#x@%#x" % (iv, i) for i, iv in codes)))
            # deep dump rec+0x30 object
            try:
                p30 = struct.unpack_from("<Q", blob0, 0x30)[0]
                inner30 = ctypes.string_at(p30, 0x60)
                _dlog("  rec+0x30 obj %#x raw: %s" % (p30, inner30.hex()))
                for i in range(0, 0x60, 8):
                    iv = struct.unpack_from("<Q", inner30, i)[0]
                    if CODE_LO + 0x1000 <= iv < CODE_HI:
                        _dlog("    rec+0x30 obj +%#x -> %#x CODE" % (i, iv))
            except Exception:
                pass
            # follow heap object pointers found in record and look for code ptrs inside
            for off in range(0x30, 0xA0, 0x18):
                try:
                    obj = struct.unpack_from("<Q", blob0, off)[0]
                except Exception:
                    continue
                if not (0x10000 <= obj < 0x7FFFFFFFFFFF) or obj in (0x140000000, 0x160000000):
                    continue
                try:
                    inner = ctypes.string_at(obj, 0x60)
                except Exception:
                    continue
                for i in range(0, len(inner) - 7, 8):
                    iv = struct.unpack_from("<Q", inner, i)[0]
                    if CODE_LO + 0x1000 <= iv < CODE_HI:
                        _dlog("  rec+%#x -> obj %#x +%#x = %#x CODE"
                              % (off, obj, i, iv))
            # record name is around +0x28; dump wider range
            start = h - 0x30
            span = 0x600
            try:
                blob = ctypes.string_at(start, span)
            except Exception:
                continue
            code_refs = []
            for off in range(0, len(blob) - 7, 8):
                v = struct.unpack_from("<Q", blob, off)[0]
                if CODE_LO + 0x1000 <= v < CODE_HI:
                    code_refs.append((start + off, v))
            for off, v in code_refs:
                _dlog("  %#x (+%#x) -> %#x" % (off, off - h, v))
    except Exception as e:
        _dlog("err %r" % (e,))
    _dlog("done")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
