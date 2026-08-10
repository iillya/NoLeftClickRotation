# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
b, e = pe.function_bounds(0x5E4D90)
print("bounds:", hex(b or 0), hex(e or 0))
print(dump(pe, 0x5E4D90, min(0x200, (e or 0x5E4D90 + 0x200) - 0x5E4D90)))
print("=== 0x5E4DA0 - 0x5E4E40 ===")
print(dump(pe, 0x5E4DA0, 0xA0))
