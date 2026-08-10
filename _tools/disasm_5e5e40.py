# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
print("=== 0x5E6BC0 - 0x5E6D00 (around 0x5E6C4E call) ===")
print(dump(pe, 0x5E6BC0, 0x140))
print("=== 0x5E5E40 head ===")
print(dump(pe, 0x5E5E40, 0x60))
