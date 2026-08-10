# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, x86_const

pe = ZbPE()
rva = 0x189FA50
b, e = pe.function_bounds(rva)
end = e or (rva + 0x244c)
raw = pe.read(rva, end - rva)
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

targets = list(range(0x14018A053F, 0x14018A0552))
print("scan dispatcher %#x..%#x" % (rva, end))
for ins in md.disasm(raw, 0x140000000 + rva):
    if ins.mnemonic.startswith("j") and ins.operands:
        op = ins.operands[0]
        if op.type == x86_const.X86_OP_IMM and op.imm in targets:
            print("%016x  %s %s  -> %#x" % (ins.address, ins.mnemonic, ins.op_str, op.imm))
