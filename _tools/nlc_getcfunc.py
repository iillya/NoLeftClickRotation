# -*- coding: utf-8 -*-
"""Print the real C function pointer bound to zbrush.commands.pixol_pick.

Reads the PyCFunctionObject layout of CPython to resolve the native entry:
  id(func) -> PyCFunctionObject
  +16 -> PyMethodDef* ; +8 -> ml_meth (the C function pointer)
"""

import ctypes
import os
import struct
import time

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_getcfunc.log")


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def resolve(func) -> dict:
    addr = id(func)
    ml = ctypes.c_uint64.from_address(addr + 16).value
    meth = ctypes.c_uint64.from_address(ml + 8).value
    name_ptr = ctypes.c_uint64.from_address(ml).value
    name = ctypes.string_at(name_ptr).decode("latin1", "replace")
    return {"type": type(func).__name__, "obj": addr, "ml": ml,
            "meth": meth, "name": name}


def scan_pointers(obj, n=0x180) -> list:
    addr = id(obj)
    data = ctypes.string_at(addr, n)
    hits = []
    for off in range(0, n - 7, 8):
        v = struct.unpack_from("<Q", data, off)[0]
        if 0x140000000 <= v < 0x160000000:
            hits.append((off, v))
    return hits


def scan_ptr_chain(obj, depth=3) -> None:
    seen = set()
    budget = [200]

    def walk(addr, off_desc, d):
        if d <= 0 or not addr or addr in seen or budget[0] <= 0:
            return
        seen.add(addr)
        budget[0] -= 1
        try:
            data = ctypes.string_at(addr, 0x200)
        except Exception:
            return
        for off in range(0, 0x200 - 7, 8):
            v = struct.unpack_from("<Q", data, off)[0]
            if 0x140000000 <= v < 0x160000000:
                _dlog("  %s +%#02x -> %#x (ptr chain d=%d)"
                      % (off_desc, off, v, d))
            if v > 0x10000 and v != addr:
                walk(v, "%s+%#x" % (off_desc, off), d - 1)

    walk(id(obj), "obj", depth)


def main() -> None:
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr getcfunc ===\n")
    except Exception:
        pass
    try:
        import zbrush.commands as zbc
        f = zbc.pixol_pick
        r = resolve(f)
        _dlog("pixol_pick type=%s name=%s obj=%#x ml=%#x meth=%#x"
              % (r["type"], r["name"], r["obj"], r["ml"], r["meth"]))
        for off, v in scan_pointers(f):
            _dlog("pixol_pick obj+%#02x -> %#x" % (off, v))
        scan_ptr_chain(f, 3)
        if hasattr(zbc, "get_mouse_pos"):
            r2 = resolve(zbc.get_mouse_pos)
            _dlog("get_mouse_pos type=%s name=%s obj=%#x ml=%#x meth=%#x"
                  % (r2["type"], r2["name"], r2["obj"], r2["ml"], r2["meth"]))
    except Exception as e:
        _dlog("err %r" % (e,))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
