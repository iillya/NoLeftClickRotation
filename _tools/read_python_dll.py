# -*- coding: utf-8 -*-
import struct

P = r"C:\Program Files\Maxon ZBrush 2026\python311.dll"

with open(P, "rb") as f:
    data = f.read()

pe_off = struct.unpack_from("<I", data, 0x3C)[0]
nsects, = struct.unpack_from("<H", data, pe_off + 6)
opt_size, = struct.unpack_from("<H", data, pe_off + 20)
sect_off = pe_off + 24 + opt_size
secs = []
for i in range(nsects):
    off = sect_off + i * 40
    name = data[off:off + 8].rstrip(b"\0").decode()
    vsize, va, rsize, rptr = struct.unpack_from("<IIII", data, off + 8)
    secs.append((name, va, vsize, rptr, rsize))
    print(name, hex(va), hex(vsize), hex(rptr))


def rva_to_off(rva):
    for name, va, vsize, rptr, rsize in secs:
        if va <= rva < va + vsize:
            return rptr + (rva - va)
    return None


for rva in (0x6043E8, 0x604408, 0x604428):
    off = rva_to_off(rva)
    print("\nRVA %#x -> file off %#x" % (rva, off or 0))
    if off:
        print(data[off:off + 64].hex())
        # try decode as pointer
        print("qword:", hex(struct.unpack_from("<Q", data, off)[0]))
