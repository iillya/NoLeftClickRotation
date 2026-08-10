# -*- coding: utf-8 -*-
"""Find instructions writing to [reg+0x808] (the nav/sculpt switch)."""

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
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

hits = []
for ins in md.disasm(code, 0x140000000 + text_va):
    for op in ins.operands:
        if op.type == x86_const.X86_OP_MEM and op.mem.disp == 0x808:
            hits.append((ins.address, ins.mnemonic, ins.op_str))
    if len(hits) > 100:
        break

print("refs to [..+0x808]:", len(hits))
for h in hits:
    print("%016x  %s %s" % h)
