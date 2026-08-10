# -*- coding: utf-8 -*-
"""Dump pixol_pick PyCFunctionObject extension area and follow record."""

import ctypes
import os
import struct
import time

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_obj.log")

CODE_LO = 0x140000000
CODE_HI = 0x160000000
STR_VA = 0x14DAD8EC0


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def main() -> None:
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr objdump ===\n")
    except Exception:
        pass
    try:
        import zbrush.commands as zbc
        obj = id(zbc.pixol_pick)
        _dlog("pixol_pick obj=%#x" % obj)
        # BFS from obj, look for blocks containing the name pointer
        seen = set()
        queue = [(obj, "obj", 0)]
        records = []
        while queue and len(seen) < 4000:
            addr, desc, depth = queue.pop(0)
            if not (0x10000 <= addr < 0x7FFFFFFFFFFF) or addr in seen:
                continue
            seen.add(addr)
            try:
                blob = ctypes.string_at(addr, 0x300)
            except Exception:
                continue
            found_name = False
            for off in range(0, len(blob) - 7, 8):
                v = struct.unpack_from("<Q", blob, off)[0]
                if v == STR_VA:
                    found_name = True
                    records.append((addr, off, depth, desc))
                if 0x10000 <= v < 0x7FFFFFFFFFFF and depth < 5:
                    queue.append((v, "%s+%#x" % (desc, off), depth + 1))
            if found_name:
                _dlog("RECORD at %#x name-off=%#x depth=%d via %s"
                      % (addr, off, depth, desc))
                for i in range(0, len(blob) - 7, 8):
                    v = struct.unpack_from("<Q", blob, i)[0]
                    if CODE_LO + 0x1000 <= v < CODE_HI:
                        _dlog("  rec+%#x -> %#x CODE" % (i, v))
        _dlog("total visited %d, records %d" % (len(seen), len(records)))
    except Exception as e:
        _dlog("err %r" % (e,))
    _dlog("done")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
