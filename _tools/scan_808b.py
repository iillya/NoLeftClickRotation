# -*- coding: utf-8 -*-
"""Byte-scan for disp32 0x808 occurrences in .text, disasm context."""

import sys

sys.path.insert(0, r"C:\Users\liuwenbo\Desktop\zb插件\_tools")
from zb_pe import ZbPE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = ZbPE()
text_va = text_rptr = text_size = None
for name, va, vsize, rptr, rsize in pe.sections:
    if name == ".text":
        text_va, text_rptr, text_size = va, rptr, vsize
        break

code = pe.data[text_rptr:text_rptr + text_size]
needle = bytes.fromhex("08080000")
positions = []
start = 0
while True:
    i = code.find(needle, start)
    if i < 0:
        break
    positions.append(i)
    start = i + 1
print("0x808 disp occurrences:", len(positions))

md = Cs(CS_ARCH_X86, CS_MODE_64)
writes = []
for i in positions:
    # disasm backwards ~12 bytes for context
    ctx_start = max(0, i - 14)
    raw = code[ctx_start:i + 7]
    insns = list(md.disasm(raw, 0x140000000 + text_va + ctx_start))
    if insns:
        last = insns[-1]
        if "0x808" in last.op_str and last.mnemonic.startswith(("mov", "or", "and", "xor", "inc", "dec", "add", "sub")):
            # keep only writes to memory with reg base (not rsp/rbp stack locals where possible)
            writes.append((last.address, last.mnemonic, last.op_str))
print("all write-class refs to 0x808:", len(writes))
for w in writes:
    print("%016x  %s %s" % w)
