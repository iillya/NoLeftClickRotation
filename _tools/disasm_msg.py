# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
# cmp rax, 0x201 at VA 0x14D9CAE39 -> RVA 0xD9CAE39
b, e = pe.function_bounds(0xD9CAE39)
print("bounds:", hex(b or 0), hex(e or 0))
print(dump(pe, 0xD9CAC70, 0x2D3))
