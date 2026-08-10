# -*- coding: utf-8 -*-
import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")

P = r"C:\Program Files\Maxon ZBrush 2026\python311.dll"

with open(P, "rb") as f:
    data = f.read()

pe_off = struct.unpack_from("<I", data, 0x3C)[0]
nsects, = struct.unpack_from("<H", data, pe_off + 6)
opt_size, = struct.unpack_from("<H", data, pe_off + 20)
sect_off = pe_off + 24 + opt_size
secs = []
image_base, = struct.unpack_from("<Q", data, pe_off + 24 + 24)
for i in range(nsects):
    off = sect_off + i * 40
    name = data[off:off + 8].rstrip(b"\0").decode()
    vsize, va, rsize, rptr = struct.unpack_from("<IIII", data, off + 8)
    secs.append((name, va, vsize, rptr, rsize))


def rva_to_off(rva):
    for name, va, vsize, rptr, rsize in secs:
        if va <= rva < va + vsize:
            return rptr + (rva - va)
    return None


from capstone import Cs, CS_ARCH_X86, CS_MODE_64

DLL_BASE = 0x7FF8DA360000
candidates = [
    0xA09DB0,  # rec+0x1a8
    0xA16E80,  # rec+0x1b0
    0x998B90,  # rec+0x1b8
    0x96ED80,  # rec+0x1c0
    0xA0F710,  # rec+0x1d0
    0xABA148,  # rec+0x1e0
    0x9E1B20,  # rec+0x1f0
]

md = Cs(CS_ARCH_X86, CS_MODE_64)
for rva in candidates:
    off = rva_to_off(rva)
    if not off:
        print("no off", hex(rva))
        continue
    raw = data[off:off + 0x120]
    print("\n===== python311.dll RVA %#x (VA %#x) =====" % (rva, DLL_BASE + rva))
    for ins in md.disasm(raw, image_base + rva):
        print("%016x  %-26s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
