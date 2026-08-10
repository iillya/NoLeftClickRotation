# -*- coding: utf-8 -*-
import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
text_va = text_rptr = text_size = None
for name, va, vsize, rptr, rsize in pe.sections:
    if name == ".text":
        text_va, text_rptr, text_size = va, rptr, vsize
        break

code = pe.data[text_rptr:text_rptr + text_size]


def callers(target):
    hits = []
    i = 0
    n = len(code)
    while i < n - 4:
        b = code[i]
        if b == 0xE8:
            rel = struct.unpack_from("<i", code, i + 1)[0]
            tgt = 0x140000000 + text_va + i + 5 + rel
            if tgt == target:
                hits.append(0x140000000 + text_va + i)
            i += 5
        else:
            i += 1
    return hits


for t in (0x1405F0FC0, 0x1405F3880):
    print("callers of %#x:" % t)
    for h in callers(t):
        b, e = pe.function_bounds(h - 0x140000000)
        print("  %#x (in func %#x..%#x)" % (h, (b or 0) + 0x140000000,
                                             (e or 0) + 0x140000000))
    if not callers(t):
        print("  none (direct)")

print("\n=== 0x5F3880 context (0x5F38C0 - 0x5F39A0) ===")
print(dump(pe, 0x5F38C0, 0xE0))
