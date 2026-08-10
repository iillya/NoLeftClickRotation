# -*- coding: utf-8 -*-
"""ZBrush 2026 视图控制代码分析（capstone 分区扫描版，快速）。
保存到 out/：
- functions.txt          全部函数清单
- region_writes.txt      视图状态写入指令（disp 0x1E0..0x210）
- region_consts.txt      圆周率/弧度常量引用
- callgraph_pipeline.txt 导航管线调用图
- nav_disasm_*.txt       关键函数反汇编
"""

import os
import struct
import sys
import bisect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from zb_pe import ZbPE
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

pe = ZbPE()
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.skipdata = True

# 导航相关代码区域
REGIONS = [
    (0x1800000, 0x1812000, "router+dispatcher"),
    (0x5E0000, 0x620000, "controller"),
    (0x17A0000, 0x17E0000, "wndproc/view"),
    (0x1830000, 0x1840000, "mouse-path"),
    (0x1804000, 0x1806000, "drag/cursor"),
]

WRITE_DISP_LO, WRITE_DISP_HI = 0x1E0, 0x210
CONSTS = {
    0x40490FDB: "pi", 0x40C90FDB: "2pi", 0x3FC90FDB: "pi/2",
    0x3C8EFA35: "deg2rad", 0x42652EE1: "rad2deg",
}
STORE_MN = {"mov", "movss", "movsd", "movups", "movdqu", "movaps", "movdqa",
            "movd", "movq", "add", "sub", "inc", "dec", "and", "or", "xor",
            "lea", "vmovss", "vmovsd", "vmovups", "vmovdqu", "vmovaps",
            "vmovdqa", "vaddss", "vsubss", "vxorps", "movzx", "movsxd"}

# 函数清单
ranges = pe.pdata_ranges()
with open(os.path.join(OUT, "functions.txt"), "w", encoding="utf-8") as f:
    for b, e, u in ranges:
        f.write("%#x %#x %#x\n" % (b, e, e - b))
print("functions:", len(ranges))

writes = []
consts = {}
calls = {}  # caller_rva -> set(callee)

import re
rip_pat = re.compile(r"\[rip \+ 0x([0-9a-f]+)\]")

for r0, r1, name in REGIONS:
    raw = pe.read(r0, r1 - r0)
    if not raw:
        continue
    for ins in md.disasm(raw, 0x140000000 + r0):
        rva = ins.address - 0x140000000
        mn = ins.mnemonic
        if mn == "call":
            m = re.search(r"0x([0-9a-f]+)$", ins.op_str)
            if m:
                calls.setdefault(rva, set()).add(int(m.group(1), 16) - 0x140000000)
            continue
        if mn in STORE_MN and "[" in ins.op_str:
            m = re.search(r"\[([a-z0-9]+) \+ 0x([0-9a-f]+)\]", ins.op_str)
            if m and not m.group(1).startswith("rip"):
                disp = int(m.group(2), 16)
                if WRITE_DISP_LO <= disp <= WRITE_DISP_HI:
                    writes.append((rva, mn, ins.op_str, disp, name))
        m = rip_pat.search(ins.op_str)
        if m:
            t = ins.address + ins.size + int(m.group(1), 16)
            trva = t - 0x140000000
            if trva in CONSTS:
                consts.setdefault(CONSTS[trva], []).append(rva)
    print("region %s scanned" % name)

with open(os.path.join(OUT, "region_writes.txt"), "w", encoding="utf-8") as f:
    f.write("# view-state writes: disp 0x1E0..0x210\n")
    for rva, mn, ops, disp, name in writes:
        f.write("%#x  %s %s  disp=%#x  [%s]\n" % (rva, mn, ops, disp, name))
print("writes:", len(writes))

with open(os.path.join(OUT, "region_consts.txt"), "w", encoding="utf-8") as f:
    for cn, rvas in consts.items():
        f.write("### %s (%d)\n" % (cn, len(rvas)))
        for r in rvas[:300]:
            f.write("  %#x\n" % r)
print("consts:", {k: len(v) for k, v in consts.items()})

# 管线调用图
PIPELINE = [0x180A0F0, 0x1807950, 0x5E5E40, 0x5E7FAA, 0x1830600, 0x5E4D90,
            0x5E539A, 0x5F7DC0, 0x5F7890, 0x5EB390, 0x5EDFC0, 0x5F0FC0,
            0x1808643, 0x18084E7, 0x5F3800, 0x5FCD10, 0x1831300, 0x1808350,
            0x1805560, 0x1803630, 0x17BB9F0, 0xE2B210, 0x5F23C0, 0x5F3880,
            0x5F0FC0]


def func_of(rva):
    begins = [r[0] for r in ranges]
    i = bisect.bisect_right(begins, rva) - 1
    if i >= 0:
        b, e, _ = ranges[i]
        if b <= rva < e:
            return b
    return None


# 预建：函数 -> 内部直接调用集合
func_calls = {}
for c, callees in calls.items():
    fb = func_of(c)
    if fb is not None:
        func_calls.setdefault(fb, set()).update(callees)


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
        for c in sorted(func_calls.get(fb, ())):
            f.write("  call %#x\n" % c)
            queue.append(c)
print("callgraph nodes:", len(seen))

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
