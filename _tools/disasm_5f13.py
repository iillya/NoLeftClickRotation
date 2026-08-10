# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
print("=== 0x5F12C0 - 0x5F1360 ===")
print(dump(pe, 0x5F12C0, 0xA0))
print("=== 0x5F1D70 - 0x5F1EA0 (function tail) ===")
print(dump(pe, 0x5F1D70, 0x130))
