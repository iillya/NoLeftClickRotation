# -*- coding: utf-8 -*-
"""Find code referencing WM_LBUTTONDOWN (0x201)."""

import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, x86_const

pe = ZbPE()
text_va = text_rptr = text_size = None
for name, va, vsize, rptr, rsize in pe.sections:
    if name == ".text":
        text_va, text_rptr, text_size = va, rptr, vsize
        break

code = pe.data[text_rptr:text_rptr + text_size]
# byte-scan for 0x201 as imm32/dword: 01 02 00 00
needle = bytes.fromhex("01020000")
pos = []
start = 0
while True:
    i = code.find(needle, start)
    if i < 0:
        break
    pos.append(i)
    start = i + 1
print("0x201 occurrences:", len(pos))

md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
shown = 0
for i in pos:
    ctx = max(0, i - 10)
    raw = code[ctx:i + 7]
    insns = list(md.disasm(raw, 0x140000000 + text_va + ctx))
    if not insns:
        continue
    last = insns[-1]
    has_201 = False
    for op in last.operands:
        if op.type == x86_const.X86_OP_IMM and op.imm == 0x201:
            has_201 = True
        if op.type == x86_const.X86_OP_MEM and op.mem.disp == 0x201:
            has_201 = True
    if has_201:
        print("%016x  %s %s" % (last.address, last.mnemonic, last.op_str))
        shown += 1
        if shown >= 40:
            break
print("shown:", shown)
