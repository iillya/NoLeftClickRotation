# -*- coding: utf-8 -*-
"""Scan .text for rel32 jumps/calls landing inside hook windows."""

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

code = pe.data[text_rptr:text_rptr + text_size]
wins = [
    (0x1405F0FC0, 0x1405F0FD0, "5f0fc0"),
    (0x1405F3880, 0x1405F3893, "5f3880"),
    (0x1405E4D90, 0x1405E4D9D, "5e4d90"),
    (0x1405E6C31, 0x1405E6C3E, "5e6c31"),
    (0x1405E6C3E, 0x1405E6C4B, "5e6c3e"),
]

hits = {w[2]: [] for w in wins}
i = 0
n = len(code)
while i < n - 4:
    b = code[i]
    if b in (0xE8, 0xE9):
        rel = struct.unpack_from("<i", code, i + 1)[0]
        tgt = 0x140000000 + text_va + i + 5 + rel
        for lo, hi, name in wins:
            if lo <= tgt < hi:
                hits[name].append((0x140000000 + text_va + i, b, tgt))
        i += 5
    else:
        i += 1

for name, lst in hits.items():
    print("%s window: %d jumps into" % (name, len(lst)))
    for h in lst[:20]:
        print("  %#x op=%#x -> %#x" % h)
