# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE, dump

pe = ZbPE()
for rva, size in ((0x1A9148, 0x48), (0x1A7B98, 0x40)):
    print("===== %#x =====" % rva)
    print(dump(pe, rva, size))
