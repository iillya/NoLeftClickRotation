# -*- coding: utf-8 -*-
import importlib.util

spec = importlib.util.spec_from_file_location(
    "n", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_nav_obs.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

stb = bytearray()
stb += m.HOOK["orig"]
n = len(m.HOOK["orig"])
stb += b"\x48\x89\x0D" + __import__("struct").pack("<i", 0x60 - (n + 7)); n += 7
stb += b"\x80\x3D" + __import__("struct").pack("<i", 0x70 - (n + 7)) + b"\x00"; n += 7
stb += b"\x74\x07"; n += 2
stb += b"\xC6\x81\x08\x08\x00\x00\x00"; n += 7
stb += b"\x48\xFF\x05" + __import__("struct").pack("<i", 0x78 - (n + 7)); n += 7
stb += b"\x49\xBB" + __import__("struct").pack("<Q", m.HOOK["cont"])
stb += b"\x41\xFF\xE3"

md = Cs(CS_ARCH_X86, CS_MODE_64)
for ins in md.disasm(bytes(stb), 0x1000):
    print("%04x  %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
