# -*- coding: utf-8 -*-
"""NLC_Diag —— 临时诊断插件：只计数、不改行为。

目的：确定 ZBrush 2026 中"左键拖画布空白处旋转"真正经过哪些函数。
六个钩子全部采用"计数器 + 原样复刻原指令"的方式，不拦截、不提前返回，
不会改变 ZBrush 行为；计数与关键寄存器快照由定时器写入
%TEMP%\\nlr_diag.log。

钩子点（全部为"计数器 + 原样复刻原指令"，不改行为）：
  D      0x5EDFC0   手势首帧处理函数入口
  B395   0x5EE395   手势分流（cmp ebx,1）——记录 ebx 值
  VIRT   0x5EE3EE   操作虚调用 [rsi]->vtable+0x80 (rdx=0x90003)
                     ——记录 rsi / vtable / 槽函数地址
  SUB    0x5E53A3   后续帧路径（r14d!=0 时）
  F7     0x5F7DC0   后续帧动作处理 1
  F7890  0x5F7890   后续帧动作处理 2
  EB390  0x5EB390   后续帧动作处理 3
  F1D90  0x5F1D90   后续帧动作处理 4
  F0FC0  0x5F0FC0   后续帧动作处理 5
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_diag.log")

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C4447  # 'NLDD'
SUBCLASS_ID = 0x4E4C4453  # 'NLDS'

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]


def _dlog(line: str) -> None:
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _jmp(reg: bytes, target: int) -> bytes:
    return b"\x49\xBB" + struct.pack("<Q", target) + b"\x41\xFF\xE3"


def _counter_prefix(page: int) -> bytes:
    """0x00: cmp [rip+0xF9],0; je +6; inc [rip+0xF5]
    标志在 page+0x100，计数器在 page+0x104。"""
    st = bytearray()
    st += b"\x80\x3D" + struct.pack("<i", 0x100 - 7) + b"\x00"  # cmp byte [rip+0xF9],0
    st += b"\x74\x06"                                            # je +0x06
    st += b"\xFF\x05" + struct.pack("<i", 0x104 - 0x0F)          # inc dword [rip+0xF5]
    return bytes(st)


def _build_stub(page: int, body: bytes) -> bytes:
    st = bytearray()
    st += _counter_prefix(page)
    st += body
    while len(st) < 0x100:
        st.append(0xCC)
    st += b"\x01"          # +0x100 标志 = 1（启用）
    st += b"\x00" * 3
    st += b"\x00" * 4      # +0x104 计数器
    st += b"\x00" * 0x68   # +0x108.. 预留快照区
    return bytes(st)


def _rd32(addr: int) -> int:
    return ctypes.c_uint32.from_address(addr).value


def _rd64(addr: int) -> int:
    return ctypes.c_uint64.from_address(addr).value


def _write_bytes(addr: int, data: bytes) -> bool:
    try:
        old = wintypes.DWORD()
        if not kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), PAGE_READWRITE, ctypes.byref(old)):
            return False
        ctypes.memmove(addr, data, len(data))
        kernel32.VirtualProtect(ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old))
        return True
    except Exception:
        return False


# ---------------- 各钩子存根 ----------------

def _stub_D(page: int) -> bytes:
    """0x5EDFC0 入口：24 字节原序言 + 跳回 0x5EDFD8。"""
    body = bytes.fromhex("488bc455535641544156488da888faffff4881ec50060000")
    body += _jmp(b"r11", 0x1405EDFD8)
    return _build_stub(page, body)


def _stub_B395(page: int) -> bytes:
    """0x5EE395：记录 ebx，再按原逻辑分流。
    注意：0x5EE39A~0x5EE3A4 也在补丁窗口内，不能在存根里跳回该区域，
    必须把 0x5EE39A 的 cmp/je 和 0x5EE3A3 的 lea rdx 一并复刻。"""
    body = bytearray()
    body += b"\x89\x1D" + struct.pack("<i", 0x108 - (0x0F + 6))  # mov [rip+..], ebx -> +0x108
    body += b"\x83\xFB\x01"                                       # cmp ebx, 1
    body += b"\x74\x0D"                                           # je +0x0D
    body += _jmp(b"r11", 0x1405EE414)                             # ebx!=1 -> 旋转数学块
    # ebx==1 路径：复刻 0x5EE39A cmp byte [0xECD4C55],r14b
    body += b"\x48\xB8" + struct.pack("<Q", 0x14ECD4C55)          # mov rax, 标志字节
    body += b"\x44\x38\x30"                                       # cmp byte [rax], r14b
    body += b"\x74\x17"                                           # je +0x17 -> 虚调用
    # 复刻 0x5EE3A3 lea rdx,[rip+0xe6e6816]（绝对地址）
    tgt = 0x1405EE3A3 + 7 + 0x0E6E6816
    body += b"\x48\xBA" + struct.pack("<Q", tgt)                  # mov rdx, 目标
    body += _jmp(b"r11", 0x1405EE3AA)                             # 跳回 0x5EE3AA（窗口外）
    body += _jmp(b"r11", 0x1405EE3EE)                             # 虚调用路径
    return _build_stub(page, bytes(body))


def _stub_VIRT(page: int) -> bytes:
    """0x5EE3EE：记录 rsi/vtable/槽函数，原样执行虚调用后跳 0x5EE408。"""
    body = bytearray()
    body += b"\x48\x89\x35" + struct.pack("<i", 0x110 - (0x0F + 7))  # mov [rip+..], rsi -> +0x110
    body += b"\x48\x8B\x06"                                           # mov rax,[rsi]
    body += b"\x48\x89\x05" + struct.pack("<i", 0x118 - (0x0F + 7 + 3 + 7))  # mov [rip+..], rax -> +0x118
    body += b"\x48\x8B\x88\x80\x00\x00\x00"                           # mov rcx,[rax+0x80]
    body += b"\x48\x89\x0D" + struct.pack("<i", 0x120 - (0x0F + 7 + 3 + 7 + 7 + 7))  # -> +0x120
    body += b"\x45\x33\xC9"                                           # xor r9d,r9d
    body += b"\xBA\x03\x00\x09\x00"                                   # mov edx,0x90003
    body += b"\x41\xB8\xFF\xFF\xFF\xFF"                               # mov r8d,-1
    body += b"\x48\x8B\xCE"                                           # mov rcx,rsi
    body += b"\xFF\x90\x80\x00\x00\x00"                               # call [rax+0x80]
    body += _jmp(b"r11", 0x1405EE408)
    return _build_stub(page, bytes(body))


def _stub_SUB(page: int) -> bytes:
    """0x5E53A3：复刻 lea rcx,[rip+..] + call 0x1411DBA90 + cmp [rdi+0x54e],sil，
    跳回 0x5E53B6。窗口 19 字节，避免覆盖不完整。"""
    tgt = 0x1405E53A3 + 7 + 0x0E6EF736
    body = b"\x48\xB9" + struct.pack("<Q", tgt)                      # mov rcx, imm64
    body += b"\x48\xB8" + struct.pack("<Q", 0x1411DBA90)             # mov rax, call目标
    body += b"\xFF\xD0"                                               # call rax
    body += bytes.fromhex("4038b74e050000")                           # cmp byte [rdi+0x54e],sil
    body += _jmp(b"r11", 0x1405E53B6)
    return _build_stub(page, body)


def _stub_F7(page: int) -> bytes:
    """0x5F7DC0：17 字节原序言 + 跳回 0x5F7DD1（指令边界）。"""
    body = bytes.fromhex("48895c2410574883ec4083b90006000000")
    body += _jmp(b"r11", 0x1405F7DD1)
    return _build_stub(page, body)


def _stub_F7890(page: int) -> bytes:
    """0x5F7890：18 字节原序言 + 跳回 0x5F78A2。"""
    body = bytes.fromhex("48895c241048897c241855488bec4883ec50")
    body += _jmp(b"r11", 0x1405F78A2)
    return _build_stub(page, body)


def _stub_EB390(page: int) -> bytes:
    """0x5EB390：17 字节原序言 + 跳回 0x5EB3A1。"""
    body = bytes.fromhex("4055535657488d6c24c14881ecd8000000")
    body += _jmp(b"r11", 0x1405EB3A1)
    return _build_stub(page, body)


def _stub_F1D90(page: int) -> bytes:
    """0x5F1D90：16 字节原序言 + 跳回 0x5F1DA0。"""
    body = bytes.fromhex("48895c2410488974241848897c242055")
    body += _jmp(b"r11", 0x1405F1DA0)
    return _build_stub(page, body)


def _stub_F0FC0(page: int) -> bytes:
    """0x5F0FC0：入口记录 rcx(控制器) 状态快照，16 字节原序言 + 跳回
    0x5F0FD0（指令边界）。该函数后续用 [r11-0x18] 等做帧存储，跳回必须用
    rax，不能碰 r11；快照只用 r10 和 rax（volatile），不动 rcx/rdx/r8/r9。
    快照：+0x108=控制器, +0x110=[rcx+0x718]模式, +0x114=[rcx+0x600]帧计数,
    +0x118=[rcx+0x774]标志, +0x120=[rcx+0x9c0]对象A,
    +0x128=对象A vtable+0x100 函数, +0x130=[rcx+0x818]对象B(=拖拽状态+0x218),
    +0x138=对象B vtable+0x138, +0x140=对象B vtable+0x1d0,
    +0x148=对象B vtable+0x1d8, +0x150=对象B vtable+0x118,
    +0x158=对象B+0x73c 标志, +0x160=[rcx+0x6a0]操作对象。"""
    body = bytearray()
    body += b"\x48\x89\x0D" + struct.pack("<i", 0xF2)                       # -> +0x108
    body += b"\x44\x8B\x91\x18\x07\x00\x00"                                 # mov r10d,[rcx+0x718]
    body += b"\x44\x89\x15" + struct.pack("<i", 0xEC)                       # -> +0x110
    body += b"\x44\x8B\x91\x00\x06\x00\x00"                                 # mov r10d,[rcx+0x600]
    body += b"\x44\x89\x15" + struct.pack("<i", 0xE2)                       # -> +0x114
    body += b"\x44\x0F\xB6\x91\x74\x07\x00\x00"                             # movzx r10d,byte[rcx+0x774]
    body += b"\x44\x89\x15" + struct.pack("<i", 0xD7)                       # -> +0x118
    body += b"\x48\x8B\x81\xC0\x09\x00\x00"                                 # mov rax,[rcx+0x9c0]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xD1)                       # -> +0x120
    body += b"\x48\x85\xC0"                                                 # test rax,rax
    body += b"\x74\x11"                                                     # jz -> 0x65
    body += b"\x48\x8B\x00"                                                 # mov rax,[rax]
    body += b"\x48\x8B\x80\x00\x01\x00\x00"                                 # mov rax,[rax+0x100]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xC3)                       # -> +0x128
    body += b"\x48\x8B\x81\x18\x08\x00\x00"                                 # mov rax,[rcx+0x818]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xBD)                       # -> +0x130
    body += b"\x48\x85\xC0"                                                 # test rax,rax
    body += b"\x74\x55"                                                     # jz -> 0xCD（跳过 vtable 读取）
    body += b"\x4C\x8B\x10"                                                 # mov r10,[rax] (vtable)
    body += b"\x4D\x8B\x92\x38\x01\x00\x00"                                 # mov r10,[r10+0x138]
    body += b"\x4C\x89\x15" + struct.pack("<i", 0xAF)                       # -> +0x138
    body += b"\x4C\x8B\x10"                                                 # mov r10,[rax]
    body += b"\x4D\x8B\x92\xD0\x01\x00\x00"                                 # mov r10,[r10+0x1d0]
    body += b"\x4C\x89\x15" + struct.pack("<i", 0xA6)                       # -> +0x140
    body += b"\x4C\x8B\x10"                                                 # mov r10,[rax]
    body += b"\x4D\x8B\x92\xD8\x01\x00\x00"                                 # mov r10,[r10+0x1d8]
    body += b"\x4C\x89\x15" + struct.pack("<i", 0x9D)                       # -> +0x148
    body += b"\x4C\x8B\x10"                                                 # mov r10,[rax]
    body += b"\x4D\x8B\x92\x18\x01\x00\x00"                                 # mov r10,[r10+0x118]
    body += b"\x4C\x89\x15" + struct.pack("<i", 0x94)                       # -> +0x150
    body += b"\x4C\x8B\x10"                                                 # mov r10,[rax]
    body += b"\x4D\x8B\x92\x3C\x07\x00\x00"                                 # mov r10,[r10+0x73c]
    body += b"\x4C\x89\x15" + struct.pack("<i", 0x8B)                       # -> +0x158
    body += b"\x48\x8B\x81\xA0\x06\x00\x00"                                 # mov rax,[rcx+0x6a0]
    body += b"\x48\x89\x05" + struct.pack("<i", 0x85)                       # -> +0x160
    body += bytes.fromhex("4c8bdc5553498d6ba14881ecc8000000")               # 16 字节原序言
    body += b"\x48\xB8" + struct.pack("<Q", 0x1405F0FD0) + b"\xFF\xE0"      # rax 跳回
    return _build_stub(page, bytes(body))


def _stub_V17A(page: int) -> bytes:
    """0x17ABFD0 视图导航处理器入口：13 字节原序言 + 跳回 0x17ABFDD。"""
    body = bytes.fromhex("48895c240855488bec4883ec50")
    body += _jmp(b"r11", 0x14017ABFDD)
    return _build_stub(page, body)


def _stub_V17B(page: int) -> bytes:
    """0x17BBDC0 视图位置写入入口：15 字节原序言 + 跳回 0x17BBDCF。"""
    body = bytes.fromhex("48895c2410564883ec30c5fa104204")
    body += _jmp(b"r11", 0x14017BBDCF)
    return _build_stub(page, body)


def _stub_HIT(page: int) -> bytes:
    """0x180A080 画布命中测试入口：15 字节原序言 + 跳回 0x180A08F。"""
    body = bytes.fromhex("4885d274578b8184010000c5fa100a")
    body += _jmp(b"r11", 0x140180A08F)
    return _build_stub(page, body)


def _stub_ACEB0(page: int) -> bytes:
    """0x1411ACEB0 每帧角度处理器入口：捕获拖拽状态字段 + 17 字节原序言 +
    跳回 0x1411ACEC1。快照：+0x108=拖拽状态, +0x110=[+0xa0]操作对象,
    +0x118/0x120/0x128=坐标 x/y/z, +0x130=角度, +0x138=标志, +0x140=objB。"""
    body = bytearray()
    body += b"\x48\x89\x15" + struct.pack("<i", 0xF2)                       # rdx -> +0x108
    body += b"\x48\x8B\x82\xA0\x00\x00\x00"                                 # mov rax,[rdx+0xa0]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xEC)                       # -> +0x110
    body += b"\x48\x8B\x82\x70\x02\x00\x00"                                 # mov rax,[rdx+0x270]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xE6)                       # -> +0x118
    body += b"\x48\x8B\x82\x74\x02\x00\x00"                                 # mov rax,[rdx+0x274]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xE0)                       # -> +0x120
    body += b"\x48\x8B\x82\x78\x02\x00\x00"                                 # mov rax,[rdx+0x278]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xDA)                       # -> +0x128
    body += b"\x48\x8B\x82\xA0\x02\x00\x00"                                 # mov rax,[rdx+0x2a0]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xD4)                       # -> +0x130
    body += b"\x48\x8B\x82\xB8\x02\x00\x00"                                 # mov rax,[rdx+0x2b8]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xCE)                       # -> +0x138
    body += b"\x48\x8B\x82\x18\x02\x00\x00"                                 # mov rax,[rdx+0x218]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xC8)                       # -> +0x140
    body += bytes.fromhex("48895c2420574883ec30448b4160488bda")             # 17 字节原序言
    body += _jmp(b"r11", 0x1411ACEC1)
    return _build_stub(page, bytes(body))


def _stub_D88A0(page: int) -> bytes:
    """0x1412D88A0 每帧动作处理器入口：捕获拖拽状态关键字段 + 22 字节原序言 +
    跳回 0x1412D88B6。快照：+0x108=拖拽状态, +0x110=objB, +0x118=工具对象,
    +0x120=工具对象[+0xa011c]标志, +0x128/0x130=累计增量, +0x138=objB2,
    +0x140=角度, +0x148=拖拽标志。只使用 rax/r10（volatile）。"""
    body = bytearray()
    body += b"\x48\x89\x15" + struct.pack("<i", 0xF2)                       # rdx -> +0x108
    body += b"\x48\x89\x0D" + struct.pack("<i", 0xF3)                       # rcx -> +0x110
    body += b"\x48\x8B\x82\x90\x01\x00\x00"                                 # mov rax,[rdx+0x190]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xED)                       # -> +0x118
    body += b"\x48\x85\xC0"                                                 # test rax,rax
    body += b"\x74\x0E"                                                     # jz -> 0x3E
    body += b"\x4C\x8B\x90\x1C\x01\x0A\x00"                                 # mov r10,[rax+0xa011c]
    body += b"\x4C\x89\x15" + struct.pack("<i", 0xE2)                       # -> +0x120
    body += b"\x48\x8B\x82\xD0\x01\x00\x00"                                 # mov rax,[rdx+0x1d0]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xDC)                       # -> +0x128
    body += b"\x48\x8B\x82\xD4\x01\x00\x00"                                 # mov rax,[rdx+0x1d4]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xD6)                       # -> +0x130
    body += b"\x48\x8B\x82\x18\x02\x00\x00"                                 # mov rax,[rdx+0x218]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xD0)                       # -> +0x138
    body += b"\x48\x8B\x82\xA0\x02\x00\x00"                                 # mov rax,[rdx+0x2a0]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xCA)                       # -> +0x140
    body += b"\x48\x8B\x82\xB8\x02\x00\x00"                                 # mov rax,[rdx+0x2b8]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xC4)                       # -> +0x148
    body += b"\x48\x8B\x82\x4C\x01\x00\x00"                                 # mov rax,[rdx+0x14c]
    body += b"\x48\x89\x05" + struct.pack("<i", 0xBE)                       # -> +0x150
    body += bytes.fromhex("488954241048894c240855574155488dac2490c9ffff")   # 22 字节原序言
    body += _jmp(b"r11", 0x1412D88B6)
    return _build_stub(page, bytes(body))


def _stub_B33DA0(page: int) -> bytes:
    """0x140B33DA0 [obj+0x132e0] 路径处理器入口：16 字节原序言 + 跳回 0x140B33DB0。"""
    body = bytes.fromhex("48895c24205556574154554156574157")
    body += _jmp(b"r11", 0x140B33DB0)
    return _build_stub(page, body)


def _stub_FFB00(page: int) -> bytes:
    """0x1413FFB00 视图位置更新入口：14 字节原序言 + 跳回 0x1413FFB0D。"""
    body = bytes.fromhex("488bc4555356574157488d68a1")
    body += _jmp(b"r11", 0x1413FFB0D)
    return _build_stub(page, body)


def _stub_FBDB0(page: int) -> bytes:
    """0x1413FBDB0 视口钳制入口：14 字节原序言 + 跳回 0x1413FBDBD。"""
    body = bytes.fromhex("488bc4555356574156488d68a1")
    body += _jmp(b"r11", 0x1413FBDBD)
    return _build_stub(page, body)


HOOKS = [
    {"name": "D",    "rva": 0x5EDFC0,  "orig": bytes.fromhex("488bc455535641544156488da888faffff4881ec50060000"), "plen": 24, "builder": _stub_D},
    {"name": "SUB",  "rva": 0x5E53A3,  "orig": bytes.fromhex("488d0d36f76e0ee8e166bf004038b74e050000"), "plen": 19, "builder": _stub_SUB},
    {"name": "F0FC0","rva": 0x5F0FC0,  "orig": bytes.fromhex("4c8bdc5553498d6ba14881ecc8000000"), "plen": 16, "builder": _stub_F0FC0},
    {"name": "D88A0","rva": 0x12D88A0, "orig": bytes.fromhex("488954241048894c240855574155488dac2490c9ffff"), "plen": 22, "builder": _stub_D88A0},
    {"name": "V17A", "rva": 0x17ABFD0,  "orig": bytes.fromhex("48895c240855488bec4883ec50"), "plen": 13, "builder": _stub_V17A},
    {"name": "V17B", "rva": 0x17BBDC0,  "orig": bytes.fromhex("48895c2410564883ec30c5fa104204"), "plen": 15, "builder": _stub_V17B},
]

for _h in HOOKS:
    _h["addr"] = 0
    _h["stub"] = 0
    _h["active"] = False


def _patch(addr: int, page: int, plen: int) -> bool:
    if plen < 13:
        return False
    p = b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3" + b"\x90" * (plen - 13)
    return _write_bytes(addr, p)


def _install() -> bool:
    try:
        base = int(kernel32.GetModuleHandleW(None) or 0)
        if not base:
            _dlog("install FAIL: no base")
            return False
        ok = False
        for h in HOOKS:
            if h["active"]:
                ok = True
                continue
            addr = base + h["rva"]
            cur = ctypes.string_at(addr, len(h["orig"]))
            if cur != h["orig"]:
                _dlog("%s FAIL mismatch cur=%s" % (h["name"], cur.hex()))
                continue
            page = int(kernel32.VirtualAlloc(
                None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) or 0)
            if not page:
                _dlog("%s FAIL alloc" % h["name"])
                continue
            stb = h["builder"](page)
            ctypes.memmove(page, stb, len(stb))
            ctypes.c_ubyte.from_address(page + 0x100).value = 1
            if not _patch(addr, page, h["plen"]):
                _dlog("%s FAIL patch" % h["name"])
                continue
            h.update(addr=addr, stub=page, active=True)
            _dlog("%s OK stub=%#x" % (h["name"], page))
            ok = True
        return ok
    except Exception as e:
        _dlog("install EXC %r" % (e,))
        return False


def _snapshot() -> str:
    parts = []
    for h in HOOKS:
        if not h["active"]:
            continue
        parts.append("%s=%d" % (h["name"], _rd32(h["stub"] + 0x104)))
    f = next((h for h in HOOKS if h["name"] == "F0FC0"), None)
    a = next((h for h in HOOKS if h["name"] == "ACEB0"), None)
    d = next((h for h in HOOKS if h["name"] == "D88A0"), None)
    extra = []
    if f and f["active"]:
        extra.append("mode=%#x" % _rd32(f["stub"] + 0x110))
        extra.append("fr=%d" % _rd32(f["stub"] + 0x114))
        extra.append("flg=%#x" % _rd32(f["stub"] + 0x118))
        extra.append("objA=%#x" % _rd64(f["stub"] + 0x120))
        extra.append("fn100=%#x" % _rd64(f["stub"] + 0x128))
        extra.append("objB=%#x" % _rd64(f["stub"] + 0x130))
        extra.append("fn138=%#x" % _rd64(f["stub"] + 0x138))
        extra.append("fn1d0=%#x" % _rd64(f["stub"] + 0x140))
        extra.append("fn1d8=%#x" % _rd64(f["stub"] + 0x148))
        extra.append("fn118=%#x" % _rd64(f["stub"] + 0x150))
        extra.append("flg73c=%#x" % _rd32(f["stub"] + 0x158))
        extra.append("opobj=%#x" % _rd64(f["stub"] + 0x160))
    if a and a["active"]:
        extra.append("st=%#x" % _rd64(a["stub"] + 0x108))
        extra.append("op=%#x" % _rd64(a["stub"] + 0x110))
        extra.append("px=%#x" % _rd32(a["stub"] + 0x118))
        extra.append("py=%#x" % _rd32(a["stub"] + 0x120))
        extra.append("pz=%#x" % _rd32(a["stub"] + 0x128))
        extra.append("ang=%#x" % _rd32(a["stub"] + 0x130))
        extra.append("dflg=%#x" % _rd32(a["stub"] + 0x138))
        extra.append("objB2=%#x" % _rd64(a["stub"] + 0x140))
    if d and d["active"]:
        extra.append("dst=%#x" % _rd64(d["stub"] + 0x108))
        extra.append("dobj=%#x" % _rd64(d["stub"] + 0x110))
        extra.append("tool=%#x" % _rd64(d["stub"] + 0x118))
        extra.append("tflg=%#x" % _rd32(d["stub"] + 0x120))
        extra.append("dx=%#x" % _rd32(d["stub"] + 0x128))
        extra.append("dy=%#x" % _rd32(d["stub"] + 0x130))
        extra.append("dobj2=%#x" % _rd64(d["stub"] + 0x138))
        extra.append("dang=%#x" % _rd32(d["stub"] + 0x140))
        extra.append("dflg2=%#x" % _rd32(d["stub"] + 0x148))
        extra.append("dflg14c=%#x" % _rd32(d["stub"] + 0x150))
    left = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
    return " ".join(parts) + " " + " ".join(extra) + " L=%d" % int(left)


_last_line = ""


def _timer_tick():
    global _last_line
    line = _snapshot()
    if line != _last_line:
        _dlog(line)
        _last_line = line


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_TIMER and wparam == TIMER_ID:
            _timer_tick()
            return 0
    except Exception:
        pass
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProcType
def _subclass_proc(hwnd, msg, wparam, lparam, u_id, ref_data) -> int:
    try:
        return _handle_message(hwnd, msg, wparam, lparam)
    except Exception:
        pass
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


_enum_result = [None]


@WNDENUMPROC
def _enum_find(hwnd, lparam) -> bool:
    try:
        buf = ctypes.create_unicode_buffer(256)
        if user32.GetClassNameW(hwnd, buf, 256) and buf.value == "ZBrush":
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                _enum_result[0] = hwnd
                return False
    except Exception:
        pass
    return True


def main() -> None:
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== NLC_Diag ===\npid=%d\n" % os.getpid())
    except Exception:
        pass
    _dlog("main start")
    hwnd = None
    for _ in range(40):
        _enum_result[0] = None
        try:
            user32.EnumWindows(_enum_find, 0)
        except Exception:
            pass
        hwnd = _enum_result[0]
        if hwnd and comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0):
            break
        time.sleep(0.5)
    if hwnd:
        user32.SetTimer(hwnd, TIMER_ID, 200, None)
        _dlog("timer on hwnd=%#x" % (hwnd or 0))
    ok = _install()
    _dlog("install result: %s" % ok)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
