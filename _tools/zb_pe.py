# -*- coding: utf-8 -*-
"""ZBrush.exe (2026) static PE helper: RVA -> file offset, disassembly, pdata ranges."""
import struct

ZBRUSH_PATH = r"C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
IMAGE_BASE = 0x140000000


class ZbPE:
    def __init__(self, path=ZBRUSH_PATH):
        with open(path, "rb") as f:
            self.data = f.read()
        pe_off = struct.unpack_from("<I", self.data, 0x3C)[0]
        self.pe_off = pe_off
        self.machine, self.nsects, _, _, _, opt_size, _ = struct.unpack_from(
            "<HHIIIHH", self.data, pe_off + 4)
        opt_off = pe_off + 24
        self.opt_size = opt_size
        self.image_base = struct.unpack_from("<Q", self.data, opt_off + 24)[0]
        self.sections = []
        sect_off = opt_off + opt_size
        for i in range(self.nsects):
            off = sect_off + i * 40
            name = self.data[off:off + 8].rstrip(b"\0").decode("latin1", "replace")
            vsize, va, rsize, rptr = struct.unpack_from("<IIII", self.data, off + 8)
            self.sections.append((name, va, vsize, rptr, rsize))
        self._pdata = None

    def rva_to_off(self, rva):
        for name, va, vsize, rptr, rsize in self.sections:
            if va <= rva < va + vsize:
                return rptr + (rva - va)
        return None

    def read(self, rva, size):
        off = self.rva_to_off(rva)
        if off is None:
            return None
        return self.data[off:off + size]

    def u64(self, rva):
        b = self.read(rva, 8)
        return struct.unpack("<Q", b)[0] if b and len(b) == 8 else None

    def u32(self, rva):
        b = self.read(rva, 4)
        return struct.unpack("<I", b)[0] if b and len(b) == 4 else None

    def pdata_ranges(self):
        if self._pdata is not None:
            return self._pdata
        ranges = []
        # .pdata section
        for name, va, vsize, rptr, rsize in self.sections:
            if name == ".pdata":
                start = va
                end = va + vsize
                for rva in range(start, end, 12):
                    b = self.read(rva, 12)
                    if not b or len(b) < 12:
                        break
                    begin, fend, unwind = struct.unpack("<III", b)
                    ranges.append((begin, fend, unwind))
                break
        self._pdata = ranges
        return ranges

    def function_bounds(self, rva):
        for begin, end, _ in self.pdata_ranges():
            if begin <= rva < end:
                return begin, end
        return None, None


def disasm(pe, rva, size, max_instr=4000):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    raw = pe.read(rva, size)
    if raw is None:
        return []
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = False
    out = []
    for ins in md.disasm(raw, IMAGE_BASE + rva):
        out.append(ins)
        if len(out) >= max_instr:
            break
    return out


def dump(pe, rva, size, max_instr=4000, annotate=True):
    lines = []
    for ins in disasm(pe, rva, size, max_instr):
        lines.append("%016x  %-30s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    return "\n".join(lines)


if __name__ == "__main__":
    pe = ZbPE()
    for rva in (0x180A0F0, 0x17BB9F0, 0x1817020, 0x1819B90, 0x180F220):
        b, e = pe.function_bounds(rva)
        print("%#x -> bounds %#x..%#x (size %#x)" % (rva, b or 0, e or 0, (e or 0) - (b or 0)))
