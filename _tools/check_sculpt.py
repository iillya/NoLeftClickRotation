# -*- coding: utf-8 -*-
import importlib.util

spec = importlib.util.spec_from_file_location(
    "n", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_sculpt_hook.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

md = Cs(CS_ARCH_X86, CS_MODE_64)
for h in m.HOOKS:
    stb = m._build_stub(0x7FFF00000000, h["orig"], h["cont"])
    print("===== %s =====" % h["name"])
    for ins in md.disasm(stb[:0x40], 0x7FFF00000000):
        print("  %04x  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
