# -*- coding: utf-8 -*-
"""Find qword pointers to 'pixol_pick' string, then code refs to those slots."""

import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, x86_const

pe = ZbPE()
STR_RVA = 0xdad8ec0
STR_VA = 0x140000000 + STR_RVA

slots = []
for name, va, vsize, rptr, rsize in pe.sections:
    if name.startswith(".r") or name == ".data":
        data = pe.data[rptr:rptr + rsize]
        for off in range(0, len(data) - 7, 8):
            v = struct.unpack_from("<Q", data, off)[0]
            if v == STR_VA:
                slots.append(va + off)
                print("slot at RVA %#x (%s+%#x)" % (va + off, name, off))

print("slots:", len(slots))

text_va = text_rptr = text_size = None
for name, va, vsize, rptr, rsize in pe.sections:
    if name == ".text":
        text_va, text_rptr, text_size = va, rptr, vsize
        break

md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
code = pe.data[text_rptr:text_rptr + text_size]
hits = []
imm_hits = []
for ins in md.disasm(code, 0x140000000 + text_va):
    for op in ins.operands:
        if op.type == x86_const.X86_OP_MEM and op.mem.base == x86_const.X86_REG_RIP:
            ref = ins.address + ins.size + op.mem.disp
            for s in slots:
                if abs(ref - s) <= 8:
                    hits.append((ins.address, ins.mnemonic, ins.op_str, ref))
                    break
        elif op.type == x86_const.X86_OP_IMM and op.imm == STR_VA:
            imm_hits.append((ins.address, ins.mnemonic, ins.op_str))
    if len(hits) > 300:
        break

print("code refs:", len(hits))
for h in hits[:300]:
    print("%016x  %s %s  -> %#x" % h)
print("imm refs:", len(imm_hits))
for h in imm_hits[:100]:
    print("%016x  %s %s" % h)
