# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = ZbPE()
cands = [0x12D88A0, 0x12D88A0 + 0x80]
md = Cs(CS_ARCH_X86, CS_MODE_64)
for rva in cands:
    raw = pe.read(rva, 20)
    print("\n===== %#x =====" % rva)
    if raw:
        print("bytes:", raw.hex())
        for ins in md.disasm(raw, 0x140000000 + rva):
            print("  %016x %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
