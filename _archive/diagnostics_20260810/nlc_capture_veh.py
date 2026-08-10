# -*- coding: utf-8 -*-
"""临时诊断插件 v3：纯代码补丁观察（无异常、无断点、无线程上下文）。

本机环境限制：
- SetThreadContext/GetThreadContext 一律 ERROR_ACCESS_DENIED（硬件断点不可用）
- 向量异常处理器回调 Python 会闪退（页保护陷阱方案不可用）

v3 只做三件事（全部是"打跳转根 + 定时器轮询"，与之前验证安全的
nav/push 诊断插件相同，不会触发任何异常）：

1. 事件分发表入口 0x180A0F0 打 13 字节根：记录事件对象指针。
2. 路由器 0x1807950 入口打 12 字节根：记录 视图对象 / 原始事件对象 /
   原始事件类型（在根内直接读 [rdx+8]）。
3. 拖动处理器 0x1805560 入口打 15 字节根：记录调用者返回地址 / 参数。

定时器（15ms）按住 F9 时记录：
- 事件对象子对象 [obj+0x1B8] 各浮点偏移的变化（找旋转参数在哪）；
- 旋转/拖动期间经过路由器的原始事件类型序列；
- 拖动处理器的调用者。

所有内存读取用 ReadProcessMemory 完成，指针失效也不会闪退。

日志：%TEMP%\\nlr_veh.log
操作：启动 ZBrush -> Ctrl+N 清空画布 -> 按住 F9 左键拖动旋转 2~3 秒 ->
      松开。日志交回分析。
"""

import ctypes
import os
import struct
import sys
import threading
import time
from ctypes import wintypes

LOG = os.path.join(os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"),
                   "nlr_veh.log")

VK_F9 = 0x78
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CONTROL = 0x11
VK_MENU = 0x12

WM_TIMER = 0x0113
TIMER_ID = 0x4E4C5633  # 'NLCV3'
SUBCLASS_ID = 0x4E4C5633

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")


SubclassProcType = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
    ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_void_p)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
                                   ctypes.POINTER(wintypes.DWORD)]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.GetCurrentProcess.restype = wintypes.HANDLE

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.MessageBoxW.restype = ctypes.c_int
user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = ctypes.c_ssize_t
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]


# ---------------- 安全内存读取 ----------------

_hproc = None


def _read(addr, size):
    global _hproc
    if not addr or size <= 0:
        return None
    if _hproc is None:
        _hproc = kernel32.GetCurrentProcess()
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    try:
        if kernel32.ReadProcessMemory(_hproc, ctypes.c_void_p(addr), buf, size,
                                      ctypes.byref(n)):
            return buf.raw[:n.value]
    except Exception:
        pass
    return None


def _rd32(addr):
    b = _read(addr, 4)
    return struct.unpack("<I", b)[0] if b and len(b) == 4 else 0


def _rd64(addr):
    b = _read(addr, 8)
    return struct.unpack("<Q", b)[0] if b and len(b) == 8 else 0


def _rdf(addr):
    b = _read(addr, 4)
    return struct.unpack("<f", b)[0] if b and len(b) == 4 else None


def _key(vk):
    try:
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:
        return False


def _log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


# ---------------- 钩子（代码补丁根） ----------------

# 每个钩子：rva、原字节、补丁长度、根内捕获槽
HOOKS = [
    {
        "name": "DISP",
        "rva": 0x180A0F0,
        "orig": bytes.fromhex("40534883ec400fb681dd000000"),
        "plen": 13,
        # 根内捕获：obj=rcx
        "slots": {"obj": 0x300},
    },
    {
        "name": "ROUTER",
        "rva": 0x1807950,
        "orig": bytes.fromhex("48895c241055565741544155"),
        "plen": 12,
        # 根内捕获：view=rcx, raw=rdx, type=[rdx+8], x=[rdx+0x18], y=[rdx+0x1C]
        "slots": {"view": 0x400, "raw": 0x408, "type": 0x410, "x": 0x418, "y": 0x41C},
    },
    {
        "name": "DRAG",
        "rva": 0x1805560,
        "orig": bytes.fromhex("488bc4488958084889701048897820"),
        "plen": 15,
        # 根内捕获：caller=[rsp], this=rcx, delta=rdx
        "slots": {"caller": 0x500, "this": 0x508, "delta": 0x510},
    },
    {
        "name": "NAV1",
        "rva": 0x1831300,
        "orig": bytes.fromhex("48895c2410574883ec30c5fa1002"),
        "plen": 14,
        # 视图参数写入函数：view=rcx, delta=rdx
        "slots": {"cnt": 0x300, "view": 0x308, "arg": 0x310, "caller": 0x318},
    },
    {
        "name": "NAV2",
        "rva": 0x1808350,
        "orig": bytes.fromhex("8bcee8a98f0200488bcee821910200"),
        "plen": 15,
        # 导航包装函数：view=esi/rcx
        "slots": {"cnt": 0x400, "view": 0x408, "arg": 0x410, "caller": 0x418},
    },
    {
        "name": "CTRL",
        "rva": 0x1807DEC,
        "orig": bytes.fromhex("488b8eb00100004889742450"),
        "plen": 12,
        # 事件转发点：handler=[rsi+0x1B0]，目标=[handler]+0x78
        "slots": {"cnt": 0x610, "handler": 0x600, "target": 0x608},
    },
    {
        "name": "ROT",
        "rva": 0x5E5177,
        "orig": bytes.fromhex("c5fa100d55f96e0ec5f82ece"),
        "plen": 12,
        # 旋转计算块入口
        "slots": {"cnt": 0x700},
    },
    {
        "name": "MOUSE1",
        "rva": 0x1830606,
        "orig": bytes.fromhex("c4c17a1000448b8974010000"),
        "plen": 12,
        # 控制器鼠标路径（入口后第 6 字节起打补丁）
        "slots": {"cnt": 0x800, "view": 0x808},
    },
    {
        "name": "MOUSE2",
        "rva": 0x5E4D90,
        "orig": bytes.fromhex("488bc4488950105553565741564157"),
        "plen": 15,
        # 控制器动作分派
        "slots": {"cnt": 0x900, "view": 0x908},
    },
]


def _build_stub_page(page, base, h):
    slots = h["slots"]
    st = bytearray()
    custom_orig_done = False
    if "cnt" in slots:
        # inc dword ptr [rip+disp]
        st += b"\xFF\x05" + struct.pack("<i", slots["cnt"] - (len(st) + 6))
    if "handler" in slots:
        # 事件转发点：mov rcx,[rsi+0x1B0]; 记录 handler 与目标函数
        st += b"\x48\x8B\x8E\xB0\x01\x00\x00"
        st += b"\x48\x89\x0D" + struct.pack("<i", slots["handler"] - (len(st) + 7))
        st += b"\x48\x8B\x01"
        st += b"\x4C\x8B\x58\x78"
        st += b"\x4C\x89\x1D" + struct.pack("<i", slots["target"] - (len(st) + 7))
        st += b"\x48\x89\x74\x24\x50"   # mov [rsp+0x50], rsi（原第 2 条指令）
        custom_orig_done = True
    # 先按名字顺序保存寄存器
    if "obj" in slots or "view" in slots or "this" in slots:
        key = "obj" if "obj" in slots else ("view" if "view" in slots else "this")
        st += b"\x48\x89\x0D" + struct.pack("<i", slots[key] - (len(st) + 7))
    if "raw" in slots or "arg" in slots:
        key = "raw" if "raw" in slots else "arg"
        st += b"\x48\x89\x15" + struct.pack("<i", slots[key] - (len(st) + 7))
    if "delta" in slots:
        st += b"\x48\x89\x15" + struct.pack("<i", slots["delta"] - (len(st) + 7))
    for key, off in (("type", 8), ("x", 0x18), ("y", 0x1C)):
        if key in slots:
            st += b"\x8B\x42" + bytes([off])    # mov eax, [rdx+off]
            st += b"\x89\x05" + struct.pack("<i", slots[key] - (len(st) + 6))
    if "caller" in slots:
        st += b"\x48\x8B\x04\x24"               # mov rax, [rsp]
        st += b"\x48\x89\x05" + struct.pack("<i", slots["caller"] - (len(st) + 7))
    # 原始序言
    if not custom_orig_done:
        st += h["orig"]
    # 跳回
    cont = base + h["rva"] + h["plen"]
    st += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    # 数据区
    max_slot = max(slots.values()) + 8
    while len(st) < max_slot:
        st.append(0xCC)
    st += b"\x00" * 0x20
    return bytes(st)


def _install(h):
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        return False
    addr = base + h["rva"]
    try:
        if ctypes.string_at(addr, len(h["orig"])) != h["orig"]:
            _log("SKIP %s version mismatch" % h["name"])
            return False
    except Exception:
        return False
    page = int(kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE,
                                     PAGE_EXECUTE_READWRITE) or 0)
    if not page:
        return False
    st = _build_stub_page(page, base, h)
    ctypes.memmove(page, st, len(st))
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(addr), h["plen"],
                                   PAGE_READWRITE, ctypes.byref(old)):
        return False
    if h["plen"] == 12:
        patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0"
    elif h["plen"] == 13:
        patch = b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3"
    elif h["plen"] == 14:
        patch = b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3" + b"\x90"
    elif h["plen"] == 15:
        patch = b"\x49\xBB" + struct.pack("<Q", page) + b"\x41\xFF\xE3" + b"\x90\x90"
    else:
        return False
    ctypes.memmove(addr, patch, len(patch))
    kernel32.VirtualProtect(ctypes.c_void_p(addr), h["plen"], old.value,
                            ctypes.byref(old))
    h["stub"] = page
    h["addr"] = addr
    _log("HOOK OK %s addr=%#x stub=%#x plen=%d" % (h["name"], addr, page, h["plen"]))
    return True


# ---------------- 状态与轮询 ----------------


class State:
    pass


S = State()
S.hwnd = None
S.f9 = False
S.last = {}
S.snap = {}
S.snap_t = 0.0
S.tick = 0


def _get_slot(h, name):
    if "stub" not in h:
        return 0
    return _rd64(h["stub"] + h["slots"][name])


def _slot32(h, name):
    if "stub" not in h:
        return 0
    return _rd32(h["stub"] + h["slots"][name])


def _poll():
    disp = HOOKS[0]
    router = HOOKS[1]
    drag = HOOKS[2]
    obj = _get_slot(disp, "obj")
    if obj and obj != S.last.get("obj"):
        S.last["obj"] = obj
        sub = _rd64(obj + 0x1B8)
        etype = _rd32(obj + 8)
        _log("OBJ obj=%#x type=%#x sub=%#x" % (obj, etype, sub))

    rtype = _slot32(router, "type")
    rview = _get_slot(router, "view")
    rraw = _get_slot(router, "raw")
    rx = _rdf(router["stub"] + router["slots"]["x"]) if "stub" in router else None
    ry = _rdf(router["stub"] + router["slots"]["y"]) if "stub" in router else None
    if rtype and rtype != S.last.get("rtype"):
        S.last["rtype"] = rtype
        _log("ROUTE type=%#x view=%#x raw=%#x x=%s y=%s"
             % (rtype, rview, rraw, rx, ry))

    dcaller = _get_slot(drag, "caller")
    if dcaller and dcaller != S.last.get("dcaller"):
        S.last["dcaller"] = dcaller
        rva = dcaller - 0x140000000 if dcaller > 0x140000000 else 0
        dthis = _get_slot(drag, "this")
        ddelta = _get_slot(drag, "delta")
        _log("DRAG caller=%#x rva=%#x this=%#x delta=%#x"
             % (dcaller, rva, dthis, ddelta))

    for nav in (HOOKS[3], HOOKS[4]):
        if "stub" not in nav:
            continue
        c = _rd32(nav["stub"] + nav["slots"]["cnt"])
        if c and c != S.last.get(nav["name"]):
            S.last[nav["name"]] = c
            view = _get_slot(nav, "view")
            arg = _get_slot(nav, "arg")
            caller = _get_slot(nav, "caller")
            dx = _rdf(arg) if arg else None
            dy = _rdf(arg + 4) if arg else None
            rva = caller - 0x140000000 if caller and caller > 0x140000000 else 0
            _log("NAV %s n=%d caller=%#x rva=%#x view=%#x dx=%s dy=%s "
                 "L=%d R=%d C=%d A=%d"
                 % (nav["name"], c, caller, rva, view, dx, dy,
                    int(_key(VK_LBUTTON)), int(_key(VK_RBUTTON)),
                    int(_key(VK_CONTROL)), int(_key(VK_MENU))))

    ctrl = HOOKS[5]
    if "stub" in ctrl:
        tgt = _get_slot(ctrl, "target")
        ccnt = _rd32(ctrl["stub"] + ctrl["slots"]["cnt"])
        if (tgt and tgt != S.last.get("ctarget")) or (ccnt and ccnt != S.last.get("ccnt")):
            if tgt and tgt != S.last.get("ctarget"):
                S.last["ctarget"] = tgt
            if ccnt:
                S.last["ccnt"] = ccnt
            S.last["ctarget"] = tgt
            handler = _get_slot(ctrl, "handler")
            rva = tgt - 0x140000000 if tgt > 0x140000000 else 0
            _log("CTRL n=%d target=%#x rva=%#x handler=%#x L=%d R=%d C=%d A=%d"
                 % (ccnt, tgt, rva, handler,
                    int(_key(VK_LBUTTON)), int(_key(VK_RBUTTON)),
                    int(_key(VK_CONTROL)), int(_key(VK_MENU))))

    rot = HOOKS[6]
    if "stub" in rot:
        c = _rd32(rot["stub"] + rot["slots"]["cnt"])
        if c and c != S.last.get("rot"):
            S.last["rot"] = c
            _log("ROT n=%d L=%d R=%d C=%d A=%d"
                 % (c, int(_key(VK_LBUTTON)), int(_key(VK_RBUTTON)),
                    int(_key(VK_CONTROL)), int(_key(VK_MENU))))

    for mh in (HOOKS[7], HOOKS[8]):
        if "stub" not in mh:
            continue
        c = _rd32(mh["stub"] + mh["slots"]["cnt"])
        if c and c != S.last.get(mh["name"]):
            S.last[mh["name"]] = c
            view = _get_slot(mh, "view")
            _log("MOUSE %s n=%d view=%#x L=%d R=%d C=%d A=%d"
                 % (mh["name"], c, view,
                    int(_key(VK_LBUTTON)), int(_key(VK_RBUTTON)),
                    int(_key(VK_CONTROL)), int(_key(VK_MENU))))


def _candidate_pointers(obj, sub):
    """从事件对象/子对象里找可能指向'相机/视图状态'的堆指针。"""
    cands = set()
    for base in (obj, sub):
        if not base:
            continue
        raw = _read(base, 0x300)
        if not raw:
            continue
        for i in range(0, len(raw) - 8, 8):
            v = struct.unpack_from("<Q", raw, i)[0]
            # 常见堆地址范围：0x00000001xxxxxx - 0x00007fxxxxxx
            if 0x1000000 <= v <= 0x7FFFFFFFFFFF and v != base:
                cands.add(v)
            if len(cands) >= 24:
                break
    # 子对象本身优先
    if sub:
        cands.add(sub)
    return list(cands)[:12]


def _snapshot_changes():
    obj = S.last.get("obj", 0)
    if not obj:
        return
    sub = _rd64(obj + 0x1B8)
    if not sub:
        return
    left = _key(VK_LBUTTON)
    right = _key(VK_RBUTTON)
    if not (left or right):
        return
    # 收集候选对象（每 250ms 重扫一次指针，避免每次全扫）
    now = time.time()
    if now - S.snap_t > 0.25:
        S.cands = _candidate_pointers(obj, sub)
    changed = []
    snaps = {}
    for p in getattr(S, "cands", []) or []:
        raw = _read(p, 0x300)
        if not raw:
            continue
        vals = {}
        for off in range(0, 0x300, 4):
            v = struct.unpack_from("<f", raw, off)[0]
            vals[off] = v
            key = (p, off)
            old = S.snap.get(key)
            if old is not None and abs(v - old) > 1e-5 and v == v:
                changed.append((p, off, old, v))
        snaps[p] = vals
    if changed and now - S.snap_t > 0.25:
        S.snap_t = now
        # 按对象分组
        by_obj = {}
        for p, off, old, v in changed:
            by_obj.setdefault(p, []).append((off, old, v))
        parts = []
        for p, items in by_obj.items():
            items = items[:8]
            parts.append("%#x{%s}" % (p, " ".join("%+#x:%g->%g" % c for c in items)))
        _log("SNAPCHG L=%d R=%d %s"
             % (int(left), int(right), " ".join(parts[:6])))
    for p, vals in snaps.items():
        for off, v in vals.items():
            S.snap[(p, off)] = v


@SubclassProcType
def _proc(hwnd, msg, wparam, lparam, u_id, ref_data):
    try:
        if msg == WM_TIMER and wparam == TIMER_ID:
            S.tick += 1
            f9 = _key(VK_F9)
            if f9:
                if not S.f9:
                    S.f9 = True
                    _log("F9 DOWN")
                _poll()
                _snapshot_changes()
                if S.tick % 100 == 0:
                    _log("TICK n=%d rtype=%#x" % (S.tick, _slot32(HOOKS[1], "type")))
            else:
                if S.f9:
                    S.f9 = False
                    _log("F9 UP")
            return 0
    except Exception as e:
        _log("PROC ERR %r" % (e,))
        return 0
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


_proc_ref = _proc


def _find_zbrush_window():
    pid = os.getpid()
    found = [None]

    @WNDENUMPROC
    def enum_cb(h, lp):
        try:
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, cls, 256)
            if cls.value == "ZBrush":
                wpid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(wpid))
                if wpid.value == pid:
                    found[0] = h
                    return False
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(enum_cb, 0)
    except Exception:
        pass
    return found[0]


def _info_box():
    time.sleep(2.0)
    try:
        user32.MessageBoxW(
            None,
            u"观察插件已就绪。\n\n"
            u"1) 按 Ctrl+N 清空画布（如有模型）；\n"
            u"2) 按住 F9 不放；\n"
            u"3) 在画布空白处左键拖动，旋转 2~3 秒；\n"
            u"4) 松开左键和 F9。\n\n"
            u"日志：%%TEMP%%\\nlr_veh.log",
            u"NoLeftClickRotation 捕获", 0x40)
    except Exception:
        pass


def main():
    try:
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("=== capture v3 ===\npy=%s pid=%d\n" % (sys.version.split()[0], os.getpid()))
    except Exception:
        pass

    base = int(kernel32.GetModuleHandleW(None) or 0)
    if base:
        for h in HOOKS:
            try:
                cur = ctypes.string_at(base + h["rva"], len(h["orig"]))
                _log("ver %s: %s" % (h["name"],
                     "OK" if cur == h["orig"] else "MISMATCH " + cur.hex()))
            except Exception as e:
                _log("ver %s ERR %r" % (h["name"], e))

    for h in HOOKS:
        try:
            _install(h)
        except Exception as e:
            _log("INSTALL ERR %s %r" % (h["name"], e))

    hwnd = _find_zbrush_window()
    for _ in range(20):
        if hwnd:
            break
        time.sleep(0.5)
        hwnd = _find_zbrush_window()
    S.hwnd = hwnd
    if hwnd:
        ok = comctl32.SetWindowSubclass(hwnd, _proc, SUBCLASS_ID, 0)
        _log("subclass %s" % ("OK" if ok else "FAIL"))
        if ok:
            user32.SetTimer(hwnd, TIMER_ID, 15, None)
    else:
        _log("NO WINDOW")

    threading.Thread(target=_info_box, daemon=True).start()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write("FATAL %r\n" % (e,))
        except Exception:
            pass
