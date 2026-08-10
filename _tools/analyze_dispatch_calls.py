# -*- coding: utf-8 -*-
"""List all call instructions inside the dispatcher 0x189fa50."""

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

print("calls in dispatcher %#x..%#x" % (rva, end))
for ins in md.disasm(raw, 0x140000000 + rva):
    if ins.mnemonic == "call":
        detail = ins.op_str
        # resolve direct calls
        if ins.operands and ins.operands[0].type == x86_const.X86_OP_IMM:
            print("%016x  call %#x" % (ins.address, ins.operands[0].imm))
        else:
            print("%016x  call %s" % (ins.address, detail))
    elif ins.mnemonic in ("jmp", "jne", "je", "ja", "jae", "jb", "jbe", "jg", "jge", "jl", "jle", "js", "jns", "jz", "jnz", "jecxz"):
        pass
