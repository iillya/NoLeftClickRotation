# -*- coding: utf-8 -*-
import importlib.util
import struct

spec = importlib.util.spec_from_file_location(
    "nlc", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_disp_entry.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

print("orig len:", len(m._CAP_ORIG), m._CAP_ORIG.hex())
print("cont:", hex(m._CONT))
print("patch len:", len(b"\x48\xB8" + b"\x00" * 8 + b"\xFF\xE0"))

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

page = 0x7FFF12340000
stb = bytearray(m._CAP_ORIG)
stb += b"\x48\xFF\x05" + struct.pack("<i", m._REC_COUNT - 0x14)
stb += b"\x49\xBB" + struct.pack("<Q", m._CONT)
stb += b"\x41\xFF\xE3"
md = Cs(CS_ARCH_X86, CS_MODE_64)
for ins in md.disasm(bytes(stb), page):
    print("%016x %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
