# -*- coding: utf-8 -*-
"""Byte-scan .text for E8/E9 rel32 whose target lands in a window."""

import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE

pe = ZbPE()
text_va = text_rptr = text_size = None
for name, va, vsize, rptr, rsize in pe.sections:
    if name == ".text":
        text_va, text_rptr, text_size = va, rptr, vsize
        break

data = pe.data[text_rptr:text_rptr + text_size]
base_va = 0x140000000 + text_va
lo = 0x14018A053F
hi = 0x14018A0552
hits = []
i = 0
n = len(data)
while i < n - 4:
    b = data[i]
    if b in (0xE8, 0xE9):
        rel = struct.unpack_from("<i", data, i + 1)[0]
        tgt = base_va + i + 5 + rel
        if lo <= tgt < hi:
            hits.append((base_va + i, b, rel, tgt))
        i += 5
    else:
        i += 1

print("rel32 jumps into window:", len(hits))
for h in hits:
    print("at %#x op=%#x rel=%d -> %#x" % h)
