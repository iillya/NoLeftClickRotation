# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE

pe = ZbPE()
for rva, n in ((0x18a1ca3, 24), (0x1898f90, 14)):
    raw = pe.read(rva, n)
    print("%#x: %s" % (rva, raw.hex() if raw else None))
for rva in (0x18a053f, 0x18a0643, 0x18a1ca3, 0x189fa50, 0x18a0550):
    b, e = pe.function_bounds(rva)
    print("bounds %#x -> %#x..%#x (is_entry=%s)" % (rva, b or 0, e or 0, b == rva))
for rva, n in ((0x18a0643, 18), (0x18a053f, 19), (0x189fd0d, 14)):
    raw = pe.read(rva, n)
    print("%#x: %s" % (rva, raw.hex() if raw else None))
