# -*- coding: utf-8 -*-
"""静态扫描 ZBrush.exe 中所有经由 IAT 调用 SetCursor 的位置。

输出: 每个调用点的 site RVA（call 指令自身）、return RVA（call 下一条指令，
即运行时 SetCursor 钩子抓到的 caller 地址）、文件偏移。
"""

import struct
import sys


def main():
    path = r"C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    data = open(path, "rb").read()
    print("file size:", len(data))

    u16 = lambda o: struct.unpack_from("<H", data, o)[0]
    u32 = lambda o: struct.unpack_from("<I", data, o)[0]
    u64 = lambda o: struct.unpack_from("<Q", data, o)[0]

    assert u16(0) == 0x5A4D
    pe = u32(0x3C)
    assert u32(pe) == 0x00004550
    opt = pe + 24
    magic = u16(opt)
    if magic == 0x20B:
        image_base = u64(opt + 24)
        size_of_image = u32(opt + 56)
        num_sections = u16(pe + 6)
        opt_size = u16(pe + 20)
        imp_rva = u32(opt + 120)
        imp_size = u32(opt + 124)
    else:
        image_base = u32(opt + 28)
        size_of_image = u32(opt + 56)
        num_sections = u16(pe + 6)
        opt_size = u16(pe + 20)
        imp_rva = u32(opt + 104)
        imp_size = u32(opt + 108)
    print("image_base:", hex(image_base), "size:", hex(size_of_image))

    sec_off = pe + 24 + opt_size
    sections = []
    for i in range(num_sections):
        s = sec_off + i * 40
        name = data[s:s + 8].rstrip(b"\x00").decode("ascii", "replace")
        vsize = u32(s + 8)
        vaddr = u32(s + 12)
        rawsize = u32(s + 16)
        rawptr = u32(s + 20)
        sections.append((name, vaddr, vsize, rawptr, rawsize))
    for s in sections:
        print("section", s)

    def rva_to_off(rva):
        for name, vaddr, vsize, rawptr, rawsize in sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        return None

    slot_rva = None
    d = imp_rva
    idx = 0
    while idx * 20 < imp_size:
        off = rva_to_off(d + idx * 20)
        if off is None:
            break
        oft = u32(off)
        name_rva = u32(off + 12)
        ft = u32(off + 16)
        dll = "?"
        if name_rva:
            noff = rva_to_off(name_rva)
            if noff is not None:
                dll = data[noff:noff + 64].split(b"\x00", 1)[0].decode("ascii", "replace")
        if dll.lower() == "user32.dll":
            i = 0
            while True:
                int_off = rva_to_off(oft + i * 8) if oft else None
                ft_off = rva_to_off(ft + i * 8)
                if ft_off is None:
                    break
                ft_val = u64(ft_off)
                if ft_val == 0:
                    break
                name = None
                if int_off is not None:
                    entry = u64(int_off)
                    if not (entry & 0x8000000000000000):
                        noff2 = rva_to_off(entry & ~0x8000000000000000)
                        if noff2 is not None:
                            name = data[noff2 + 2:noff2 + 64].split(b"\x00", 1)[0].decode("ascii", "replace")
                if name == "SetCursor":
                    slot_rva = ft + i * 8
                    print("SetCursor IAT slot RVA:", hex(slot_rva))
                    break
                i += 1
            if slot_rva:
                break
        idx += 1

    if slot_rva is None:
        print("SetCursor slot not found")
        return

    text = None
    for name, vaddr, vsize, rawptr, rawsize in sections:
        if name in (".text", "CODE", ".textbss"):
            text = (name, vaddr, vsize, rawptr, rawsize)
            break
    if text is None:
        text = sections[0]
    tname, tvaddr, tvsize, traw, trsize = text
    print("scanning", tname, "rva", hex(tvaddr), "size", hex(trsize))

    hits = []
    end = traw + min(trsize, tvsize)
    for pat, label in ((b"\xFF\x15", "call"), (b"\xFF\x25", "jmp")):
        pos = traw
        while True:
            p = data.find(pat, pos, end - 5)
            if p == -1:
                break
            disp = u32(p + 2)
            insn_len = 6
            next_rip = tvaddr + (p - traw) + insn_len
            target = (next_rip + disp) & 0xFFFFFFFF
            if target == slot_rva:
                site_rva = tvaddr + (p - traw)
                hits.append((site_rva, label))
            pos = p + 1

    print("call/jmp sites through SetCursor IAT:", len(hits))
    hits.sort()
    for h, label in hits:
        print("  %s site rva=%#x  return=%#x  file=%#x" % (label, h, h + 6, rva_to_off(h)))


if __name__ == "__main__":
    main()
