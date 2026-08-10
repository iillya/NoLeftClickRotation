# -*- coding: utf-8 -*-
"""Scan python311.dll .text for rel32 jumps/calls into the 0x53f window."""

import struct

P = r"C:\Program Files\Maxon ZBrush 2026\python311.dll"
with open(P, "rb") as f:
    data = f.read()

pe_off = struct.unpack_from("<I", data, 0x3C)[0]
nsects, = struct.unpack_from("<H", data, pe_off + 6)
opt_size, = struct.unpack_from("<H", data, pe_off + 20)
sect_off = pe_off + 24 + opt_size
image_base, = struct.unpack_from("<Q", data, pe_off + 24 + 24)
secs = []
for i in range(nsects):
    off = sect_off + i * 40
    name = data[off:off + 8].rstrip(b"\0").decode()
    vsize, va, rsize, rptr = struct.unpack_from("<IIII", data, off + 8)
    secs.append((name, va, vsize, rptr, rsize))

text = [s for s in secs if s[0] == ".text"][0]
name, va, vsize, rptr, rsize = text
code = data[rptr:rptr + rsize]

lo = 0x14018A053F
hi = 0x14018A0552
hits = []
i = 0
n = len(code)
while i < n - 4:
    b = code[i]
    if b in (0xE8, 0xE9):
        rel = struct.unpack_from("<i", code, i + 1)[0]
        tgt = image_base + va + i + 5 + rel
        if lo <= tgt < hi:
            hits.append((image_base + va + i, b, rel, tgt))
        i += 5
    else:
        i += 1

print("python311.dll rel32 into window:", len(hits))
for h in hits:
    print("at %#x op=%#x rel=%d -> %#x" % h)
