# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = ZbPE()
md = Cs(CS_ARCH_X86, CS_MODE_64)
for rva in (0x1A91521, 0x1A7BB71):
    raw = pe.read(rva - 8, 32)
    print("===== RVA %#x =====" % rva)
    print("bytes:", raw.hex() if raw else None)
    if raw:
        for ins in md.disasm(raw, 0x140000000 + rva - 8):
            if ins.address < 0x140000000 + rva + 16:
                print("  %016x  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
