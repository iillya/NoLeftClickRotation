# -*- coding: utf-8 -*-
import struct
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE

pe = ZbPE()
STR_RVA = 0xDAD8EC0
# find section
for name, va, vsize, rptr, rsize in pe.sections:
    if va <= STR_RVA < va + vsize:
        print("string in section", name)
        off = rptr + (STR_RVA - va)
        data = pe.data[off - 0x80:off + 0x200]
        # print strings around
        import re
        strs = re.findall(rb"[\x20-\x7e]{4,}", data)
        print("nearby strings:")
        for s in strs[:40]:
            print("  ", s.decode("latin1"))
        # print qwords that look like code pointers nearby
        print("qwords near (code-range):")
        base_rva = STR_RVA - 0x80
        for i in range(0, len(data) - 7, 8):
            v = struct.unpack_from("<Q", data, i)[0]
            if 0x140000000 <= v < 0x160000000:
                print("   +%#x (rva %#x) = %#x" % (i, base_rva + i, v))
        break
