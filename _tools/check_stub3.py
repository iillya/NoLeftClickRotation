# -*- coding: utf-8 -*-
import importlib.util

spec = importlib.util.spec_from_file_location(
    "nlc", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_real_capture2.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

md = Cs(CS_ARCH_X86, CS_MODE_64)
for idx, h in enumerate(m.HOOKS):
    name = "SITE%d" % idx
    page = 0x00007FFF12340000
    stub = m._build_stub(page, h["orig"][:h["prefix"]], h["reg"], h["cont"])
    print("===== hook %s (reg=%s) =====" % (name, h["reg"]))
    for ins in md.disasm(stub[:0x60], page):
        print("%016x %-26s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    print()
