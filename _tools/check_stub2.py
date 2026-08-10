# -*- coding: utf-8 -*-
import importlib.util

spec = importlib.util.spec_from_file_location(
    "nlc", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_real_capture.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

page = 0x00007FFF12340000
stub = m._build_stub(page)

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

md = Cs(CS_ARCH_X86, CS_MODE_64)
for ins in md.disasm(stub[:0x60], page):
    print("%016x %-28s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("stub len:", len(stub))
print("patch len:", len(b"\x48\xB8" + b"\x00" * 8 + b"\xFF\xE0" + b"\x90" * 11))
