# -*- coding: utf-8 -*-
import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE

pe = ZbPE()
for name, va, vsize, rptr, rsize in pe.sections:
    print("%-10s va=%#010x vsize=%#x rptr=%#x rsize=%#x"
          % (name, va, vsize, rptr, rsize))
