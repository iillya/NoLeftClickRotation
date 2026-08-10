# -*- coding: utf-8 -*-
"""ZBrush 2026 视图控制代码系统性逆向分析。

产出（保存到 out/）：
- functions.txt          全部函数（pdata）清单
- callgraph_pipeline.txt 导航管线相关函数的调用图
- view_state_writes.txt  写入视图状态字段（[reg+0x1B8+0x3C..0x48] 等）的指令
- rotation_consts.txt    引用圆周率/弧度换算等常量的函数
- nav_disasm_*.txt       导航管线关键函数完整反汇编
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zb_pe import ZbPE
from iced_x86 import Decoder, DecoderOptions, Mnemonic, Register, OpKind

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

pe = ZbPE()

# ---------------- 1. 函数清单 ----------------
ranges = pe.pdata_ranges()
with open(os.path.join(OUT, "functions.txt"), "w", encoding="utf-8") as f:
    f.write("# function rva, end, size\n")
    for b, e, u in ranges:
        f.write("%#x %#x %#x\n" % (b, e, e - b))
print("functions:", len(ranges))

# ---------------- 2. 全量扫描 ----------------
RAW = pe.read(0x1000, 0xDA1F3E0)
dec = Decoder(64, RAW, 0, DecoderOptions.NONE)

WRITE_DISP_LO, WRITE_DISP_HI = 0x1E0, 0x210

PI = 0x40490FDB
PI2 = 0x40C90FDB
PI_HALF = 0x3FC90FDB
DEG2RAD = 0x3C8EFA35
RAD2DEG = 0x42652EE1
CONSTS = {
    PI: "pi", PI2: "2pi", PI_HALF: "pi/2", DEG2RAD: "deg2rad", RAD2DEG: "rad2deg",
}

WRITE_MNEMONICS = {
    Mnemonic.MOV, Mnemonic.MOVSS, Mnemonic.MOVSD, Mnemonic.MOVUPS,
    Mnemonic.MOVDQU, Mnemonic.MOVAPS, Mnemonic.MOVDQA, Mnemonic.MOVD,
    Mnemonic.MOVQ, Mnemonic.ADD, Mnemonic.SUB, Mnemonic.INC, Mnemonic.DEC,
    Mnemonic.AND, Mnemonic.OR, Mnemonic.XOR, Mnemonic.LEA,
}

view_writes = []
const_refs = {}
all_calls = {}

n = 0
for ins in dec:
    n += 1
    if n % 5000000 == 0:
        print("scanned %dM instructions..." % (n // 1000000))
    mn = ins.mnemonic
    if mn == Mnemonic.CALL:
        t = ins.near_branch_target
        if t:
            all_calls.setdefault(ins.ip + 0x1000, set()).add(t + 0x1000)
        continue
    if ins.op_count and ins.op0_kind == OpKind.MEMORY:
        disp = ins.memory_displacement
        if mn in WRITE_MNEMONICS and WRITE_DISP_LO <= disp <= WRITE_DISP_HI:
            view_writes.append((ins.ip + 0x1000, mn, str(ins), disp))
        elif ins.memory_base == Register.RIP:
            t = ins.ip + ins.len + disp + 0x1000
            if t in CONSTS:
                const_refs.setdefault(CONSTS[t], []).append(ins.ip + 0x1000)

with open(os.path.join(OUT, "view_state_writes.txt"), "w", encoding="utf-8") as f:
    f.write("# instructions with memory displacement 0x1E0..0x210\n")
    for rva, mn, ops, disp in view_writes:
        f.write("%#x  %s %s   disp=%#x\n" % (rva, mn, ops, disp))
print("view writes:", len(view_writes))

with open(os.path.join(OUT, "rotation_consts.txt"), "w", encoding="utf-8") as f:
    for name, rvas in const_refs.items():
        f.write("### %s (%d refs)\n" % (name, len(rvas)))
        for r in rvas[:400]:
            f.write("  %#x\n" % r)
print("const refs:", {k: len(v) for k, v in const_refs.items()})

# ---------------- 3. 导航管线调用图 ----------------
PIPELINE = [0x180A0F0, 0x1807950, 0x5E5E40, 0x5E7FAA, 0x1830600, 0x5E4D90,
            0x5E539A, 0x5F7DC0, 0x5F7890, 0x5EB390, 0x5EDFC0, 0x5F0FC0,
            0x1808643, 0x18084E7, 0x5F3800, 0x5FCD10, 0x1831300, 0x1808350,
            0x1805560, 0x1803630, 0x17BB9F0, 0xE2B210]


def func_of(rva):
    for b, e, _ in ranges:
        if b <= rva < e:
            return b
    return None


with open(os.path.join(OUT, "callgraph_pipeline.txt"), "w", encoding="utf-8") as f:
    seen = set()
    queue = list(PIPELINE)
    while queue:
        rva = queue.pop(0)
        if rva in seen:
            continue
        seen.add(rva)
        f.write("=== %#x ===\n" % rva)
        fb = func_of(rva)
        calls = set()
        for c, callees in all_calls.items():
            if func_of(c) == fb:
                calls |= callees
        for c in sorted(calls):
            f.write("  call %#x\n" % c)
            queue.append(c)
print("pipeline callgraph saved, nodes:", len(seen))

# ---------------- 4. 关键函数反汇编 ----------------
from zb_pe import dump as zb_dump
for rva in PIPELINE:
    b, e = pe.function_bounds(rva)
    size = min(((e or rva + 0x200) - rva) + 0x40, 0x600)
    try:
        text = zb_dump(pe, rva, size, max_instr=4000)
        with open(os.path.join(OUT, "nav_disasm_%x.txt" % rva),
                  "w", encoding="utf-8", errors="replace") as f:
            f.write(text)
    except Exception as ex:
        print("disasm fail", hex(rva), ex)
print("done")
