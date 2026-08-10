# -*- coding: utf-8 -*-
import importlib.util
import struct

spec = importlib.util.spec_from_file_location(
    "n", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_808hook.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

stb = bytearray()
stb += bytes.fromhex("48898308080000")
stb += b"\x48\x89\x1D" + struct.pack("<i", 0x60 - 0x0E)
stb += b"\x80\x3D" + struct.pack("<i", 0x70 - 0x15) + b"\x00"
stb += b"\x74\x0B"
stb += b"\x48\xC7\x83\x08\x08\x00\x00\x00\x00\x00\x00"
stb += bytes.fromhex("488b8300080000")
stb += b"\x48\xFF\x05" + struct.pack("<i", 0x78 - 0x30)
stb += b"\x49\xBB" + struct.pack("<Q", m.HOOK["cont"])
stb += b"\x41\xFF\xE3"

md = Cs(CS_ARCH_X86, CS_MODE_64)
for ins in md.disasm(bytes(stb), 0x1000):
    print("%04x  %-30s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
