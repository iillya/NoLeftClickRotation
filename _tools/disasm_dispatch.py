# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
rva = 0x189FA50
b, e = pe.function_bounds(rva)
print("bounds:", hex(b or 0), hex(e or 0), "size:", hex((e or 0) - (b or 0)))
end = e or (rva + 0x1200)
print(dump(pe, rva, min(0x1200, end - rva)))
