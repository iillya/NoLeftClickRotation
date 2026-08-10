# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
for rva in (0x18ab910, 0x18ab2e0, 0x18ac370, 0x18ac400,
            0x18974a0, 0x18973e0, 0x18ac9b0, 0x1898f90):
    b, e = pe.function_bounds(rva)
    print("\n===== %#x bounds %#x..%#x size=%#x ====="
          % (rva, b or 0, e or 0, (e or 0) - (b or 0)))
    end = e or (rva + 0x80)
    print(dump(pe, rva, min(0x120, end - rva)))
