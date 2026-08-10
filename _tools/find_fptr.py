# -*- coding: utf-8 -*-
"""Scan data sections for qwords pointing to candidate code addresses."""

import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE

pe = ZbPE()
cands = {
    0x18a053f: "siteB",
    0x18a0643: "siteA",
    0x18a1ca3: "late",
    0x189fd19: "early",
    0x18ab910: "wrapper1",
    0x18ac370: "wrapper2",
    0x18a0550: "callrax",
}
va_by_rva = {}

found = {c: [] for c in cands}
for name, va, vsize, rptr, rsize in pe.sections:
    if name.startswith(".r") or name == ".data" or name == "_RDATA":
        data = pe.data[rptr:rptr + rsize]
        for off in range(0, len(data) - 7, 8):
            v = struct.unpack_from("<Q", data, off)[0]
            va_here = va + off
            for rva, label in cands.items():
                if v == 0x140000000 + rva:
                    found[rva].append((name, va_here, off))

for rva, label in cands.items():
    hits = found[rva]
    print("%s %#x: %d refs" % (label, 0x140000000 + rva, len(hits)))
    for name, va_here, off in hits[:20]:
        print("   %s+%#x (RVA %#x)" % (name, off, va_here))
