# -*- coding: utf-8 -*-
import importlib.util
import struct

spec = importlib.util.spec_from_file_location(
    "nlc", r"C:\Users\liuwenbo\Desktop\zb插件\_tools\nlc_lambda_capture.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

page = 0x00007FFF12340000
stub = m._build_stub(page)
print("stub len", len(stub))

from capstone import Cs, CS_ARCH_X86, CS_MODE_64

md = Cs(CS_ARCH_X86, CS_MODE_64)
for ins in md.disasm(stub[:0x50], page):
    print("%016x %-24s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

CONT = 0x1401898F9E
imm = struct.unpack("<Q", stub[0x46:0x4E])[0]
print("mov r11 imm:", hex(imm), "expected:", hex(CONT))
print("jmp r11 bytes:", stub[0x4E:0x51].hex(), "expected: 41ffe3")
d1 = struct.unpack("<i", stub[0x11:0x15])[0]
print("rec lambda target:", hex(0x15 + d1), "expected:", hex(m._REC_LAMBDA))
d2 = struct.unpack("<i", stub[0x18:0x1C])[0]
print("lea buf target:", hex(0x1C + d2), "expected:", hex(m._REC_BUF))
d3 = struct.unpack("<i", stub[0x1F:0x23])[0]
print("counter load target:", hex(0x23 + d3), "expected:", hex(m._REC_COUNT))
d4 = struct.unpack("<i", stub[0x2C:0x30])[0]
print("counter store target:", hex(0x30 + d4), "expected:", hex(m._REC_COUNT))
d5 = struct.unpack("<i", stub[0x3B:0x3F])[0]
print("lambda reload target:", hex(0x3F + d5), "expected:", hex(m._REC_LAMBDA))
