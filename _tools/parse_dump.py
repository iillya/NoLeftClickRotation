# -*- coding: utf-8 -*-
"""Parse a Windows minidump: exception record + faulting thread context."""

import os
import struct
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\liuwenbo\AppData\Local\CrashDumps\ZBrush.exe.22072.dmp"

f = open(PATH, "rb")

sig, ver, numstreams, dir_rva = struct.unpack("<IIII", f.read(16))
print("signature=%#x version=%d streams=%d dir_rva=%#x" % (sig, ver, numstreams, dir_rva))

entries = []
f.seek(dir_rva)
for _ in range(numstreams):
    stype, dsize, rva = struct.unpack("<III", f.read(12))
    entries.append((stype, dsize, rva))


def read_at(rva, size):
    f.seek(rva)
    return f.read(size)


exc = None
for stype, dsize, rva in entries:
    if stype == 6:  # ExceptionStream
        data = read_at(rva, 40)
        print("exc stream dsize=%d read=%d" % (dsize, len(data)))
        print("exc raw:", data[:40].hex())
        tid, = struct.unpack("<I", data[:4])
        code, flags, record, addr, paramcnt = struct.unpack("<IIQQI", data[4:32])
        exc = {"tid": tid, "code": code, "addr": addr, "record": record,
               "paramcnt": paramcnt}
        print("EXCEPTION stream: tid=%d code=%#x addr=%#x record=%#x params=%d"
              % (tid, code, addr, record, paramcnt))

threads = []
mem_ranges = []
thread_stacks = []
for stype, dsize, rva in entries:
    if stype == 3:  # ThreadListStream
        cnt, = struct.unpack("<I", read_at(rva, 4))
        off = rva + 4
        for i in range(cnt):
            data = read_at(off + i * 48, 48)
            tid, suspend, priocl, prio = struct.unpack("<IIII", data[0:16])
            teb, = struct.unpack("<Q", data[16:24])
            stack_start, stack_loc_rva = struct.unpack("<QQ", data[24:40])
            ctx_size, ctx_rva = struct.unpack("<II", data[40:48])
            threads.append((tid, ctx_rva, ctx_size))
            thread_stacks.append((tid, stack_start))
        print("threads:", cnt)
    elif stype == 9:  # Memory64ListStream
        cnt, = struct.unpack("<Q", read_at(rva, 8))
        data_off = rva + 8 + cnt * 16
        for i in range(cnt):
            start, size = struct.unpack("<QQ", read_at(rva + 8 + i * 16, 16))
            mem_ranges.append((start, size, data_off))
            data_off += size
        print("mem64 ranges:", cnt)
    elif stype == 5:  # MemoryListStream
        cnt, = struct.unpack("<I", read_at(rva, 4))
        off = rva + 4
        for i in range(cnt):
            start, size, mrva = struct.unpack("<QQI", read_at(off + i * 24, 20))
            mem_ranges.append((start, size, mrva))
        print("mem ranges:", cnt)


def read_mem(addr, size=8):
    for start, rsize, mrva in mem_ranges:
        if start <= addr < start + rsize and addr + size <= start + rsize:
            return read_at(mrva + (addr - start), size)
    return None


def parse_context(ctx):
    flags, = struct.unpack("<I", ctx[0x30:0x34])
    eflags, = struct.unpack("<I", ctx[0x44:0x48])
    segcs, = struct.unpack("<H", ctx[0x38:0x3A])
    rax, = struct.unpack("<Q", ctx[0x78:0x80])
    rcx, = struct.unpack("<Q", ctx[0x80:0x88])
    rdx, = struct.unpack("<Q", ctx[0x88:0x90])
    rbx, = struct.unpack("<Q", ctx[0x90:0x98])
    rsp, = struct.unpack("<Q", ctx[0x98:0xA0])
    rbp, = struct.unpack("<Q", ctx[0xA0:0xA8])
    rsi, = struct.unpack("<Q", ctx[0xA8:0xB0])
    rdi, = struct.unpack("<Q", ctx[0xB0:0xB8])
    r8, = struct.unpack("<Q", ctx[0xB8:0xC0])
    r9, = struct.unpack("<Q", ctx[0xC0:0xC8])
    r10, = struct.unpack("<Q", ctx[0xC8:0xD0])
    r11, = struct.unpack("<Q", ctx[0xD0:0xD8])
    r12, = struct.unpack("<Q", ctx[0xD8:0xE0])
    r13, = struct.unpack("<Q", ctx[0xE0:0xE8])
    r14, = struct.unpack("<Q", ctx[0xE8:0xF0])
    r15, = struct.unpack("<Q", ctx[0xF0:0xF8])
    rip, = struct.unpack("<Q", ctx[0xF8:0x100])
    return {"flags": flags, "eflags": eflags, "segcs": segcs,
            "rax": rax, "rcx": rcx, "rdx": rdx, "rbx": rbx, "rsp": rsp,
            "rbp": rbp, "rsi": rsi, "rdi": rdi, "r8": r8, "r9": r9,
            "r10": r10, "r11": r11, "r12": r12, "r13": r13, "r14": r14,
            "r15": r15, "rip": rip}


if exc:
    for tid, ctx_rva, ctx_size in threads:
        if tid == exc["tid"]:
            ctx = read_at(ctx_rva, min(ctx_size, 0x400))
            regs = parse_context(ctx)
            print("FAULTING THREAD %d" % tid)
            print("  ContextFlags=%#x EFlags=%#x SegCs=%#x" % (
                regs["flags"], regs["eflags"], regs["segcs"]))
            sp = regs["rsp"]
            in_stack = [t for t, s in thread_stacks if abs(s - sp) < 0x100000]
            print("  rsp in thread stacks (start within 1MB): %s" % in_stack[:8])
            for k, v in regs.items():
                print("  %-4s = %#x" % (k, v))
            # probe memory: [r13+0x30] and [rax]
            p1 = regs["r13"] + 0x30
            p2 = regs["rax"]
            for label, addr in (("[r13+0x30]", p1), ("[rax]", p2),
                                ("[rsp+0x70]", regs["rsp"] + 0x70),
                                ("[rsp+0x1c0]", regs["rsp"] + 0x1c0)):
                b = read_mem(addr, 8)
                print("  %-12s %#x -> %s" % (label, addr,
                                              hex(struct.unpack("<Q", b)[0]) if b else "N/A"))
            # stub slots (from nlr_real2.log)
            stub = 0x45A70000
            for label, off in (("stub+0x80 r13", 0x80), ("stub+0x88 fn", 0x88),
                               ("stub+0x90 retval", 0x90), ("stub+0x98 rsp", 0x98)):
                b = read_mem(stub + off, 8)
                print("  %-16s %#x -> %s" % (label, stub + off,
                                              hex(struct.unpack("<Q", b)[0]) if b else "N/A"))
            # dump stack around rsp
            sp = regs["rsp"]
            print("  stack around rsp:")
            for i in range(16):
                b = read_mem(sp + i * 8, 8)
                if b:
                    print("    rsp+%#x = %#x" % (i * 8, struct.unpack("<Q", b)[0]))
            break

f.close()
