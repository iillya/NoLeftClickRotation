# -*- coding: utf-8 -*-
"""Find string 'pixol_pick' in ZBrush.exe and scan code for references."""

import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE

pe = ZbPE()
needle = b"pixol_pick\x00"
start = 0
positions = []
while True:
    pos = pe.data.find(needle, start)
    if pos < 0:
        break
    positions.append(pos)
    start = pos + 1
print("occurrences:", len(positions), [hex(p) for p in positions])
if not positions:
    sys.exit()

for pos in positions:
    rva = None
    for name, va, vsize, rptr, rsize in pe.sections:
        if rptr <= pos < rptr + rsize:
            rva = va + (pos - rptr)
            break
    print("string at file", hex(pos), "RVA", hex(rva) if rva else None)

target_rvas = []
for pos in positions:
    for name, va, vsize, rptr, rsize in pe.sections:
        if rptr <= pos < rptr + rsize:
            target_rvas.append(va + (pos - rptr))
            break

from capstone import Cs, CS_ARCH_X86, CS_MODE_64, x86_const

text_va = text_rptr = text_size = None
for name, va, vsize, rptr, rsize in pe.sections:
    if name == ".text":
        text_va, text_rptr, text_size = va, rptr, vsize
        break

md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
code = pe.data[text_rptr:text_rptr + text_size]
hits = []
for ins in md.disasm(code, 0x140000000 + text_va):
    for op in ins.operands:
        if op.type == x86_const.X86_OP_MEM and op.mem.base == x86_const.X86_REG_RIP:
            disp = op.mem.disp
            ref = ins.address + ins.size + disp
            for tr in target_rvas:
                if abs(ref - (0x140000000 + tr)) <= 0x10:
                    hits.append((ins.address, ins.mnemonic, ins.op_str, ref))
                    break
    if len(hits) > 200:
        break

print("references found:", len(hits))
for h in hits[:200]:
    print("%016x  %s %s  -> %#x" % h)
