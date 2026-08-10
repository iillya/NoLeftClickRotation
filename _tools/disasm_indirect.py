# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
for rva, size in ((0x189fce0, 0x90), (0x18a0510, 0x80),
                  (0x18a0600, 0x90), (0x18a1c50, 0xb0)):
    print("\n===== %#x =====" % rva)
    print(dump(pe, rva, size))
