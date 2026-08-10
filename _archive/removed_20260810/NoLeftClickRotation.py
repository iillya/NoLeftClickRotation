# -*- coding: utf-8 -*-
"""自动测试：加载球体 + 锁定相机 + 模拟拖拽，全量记录检测信号。

记录每个采样点的：画布坐标、[rdx+0xa0] 命中记录、pixol mat/n/kind。
用于确定"空白->模型"拖拽期间可用的模型检测信号。
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

DEBUG_LOG: str = os.path.join(
    os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_hit.log"
)

try:
    with open(DEBUG_LOG, "w", encoding="utf-8") as _f:
        _f.write("=== module load ===\n")
except Exception:
    pass

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_TIMER = 0x0113

VK_LBUTTON = 0x01
TIMER_ID = 0x4E4C5449
SUBCLASS_ID = 0x4E4C5449

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p,
)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32 = ctypes.windll.user32
comctl32 = ctypes.WinDLL("comctl32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.mouse_event.restype = None
user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                               wintypes.DWORD, ctypes.c_void_p]
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_WHEEL = 0x0800
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND, SubclassProcType, ctypes.c_size_t, ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualAlloc.argtypes = [
    ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD,
]
kernel32.VirtualProtect.restype = wintypes.BOOL
kernel32.VirtualProtect.argtypes = [
    ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

# ---------------- 命中记录钩子 ----------------

HIT_RVA = 0x12D88A0
HIT_ORIG = bytes.fromhex("488954241048894c240855574155488dac2490c9ffff")

# 记录拖拽状态（rdx）的多个字段：flag 在 stub+0xC0，值在 stub+0xC8+8*i
RECORD_OFFSETS = (0x90, 0xA0, 0xB0, 0xC0, 0xE0, 0xE8, 0x190, 0x1C8, 0x1D0, 0x210)
STUB_FLAG = 0xC0
STUB_VALS = 0xC8
STUB_CNT = 0x118

_hit = {"addr": 0, "stub": 0, "active": False}


def _dlog(line: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass


def _write_bytes(addr: int, data: bytes) -> bool:
    try:
        old = wintypes.DWORD()
        if not kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), PAGE_READWRITE, ctypes.byref(old)
        ):
            return False
        ctypes.memmove(addr, data, len(data))
        kernel32.VirtualProtect(
            ctypes.c_void_p(addr), len(data), old.value, ctypes.byref(old)
        )
        return True
    except Exception:
        return False


def _hit_install() -> bool:
    if _hit["active"]:
        return True
    base = int(kernel32.GetModuleHandleW(None) or 0)
    if not base:
        _dlog("install FAIL no base")
        return False
    addr = base + HIT_RVA
    if ctypes.string_at(addr, len(HIT_ORIG)) != HIT_ORIG:
        _dlog("install FAIL orig mismatch: %s" % ctypes.string_at(addr, 22).hex())
        return False
    page = kernel32.VirtualAlloc(None, 0x1000, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not page:
        _dlog("install FAIL alloc")
        return False
    page = int(page)
    cont = addr + len(HIT_ORIG)
    stb = bytearray()
    # 0x00: cmp byte [rip+0x??],0   （disp 稍后填，flag 在 0xC0）
    stb += b"\x80\x3D" + struct.pack("<i", 0) + b"\x00"
    # 0x07: je PASS（disp 稍后填）
    je_pos = len(stb)
    stb += b"\x74\x00"
    # 0x09: inc dword [rip+0x??]  （调用计数器 @ STUB_CNT）
    cnt_pos = len(stb)
    stb += b"\xFF\x05" + struct.pack("<i", 0)
    # 记录块：每个字段 mov rax,[rdx+off]; mov [rip+disp],rax
    rec_starts = []
    for i, off in enumerate(RECORD_OFFSETS):
        rec_starts.append(len(stb))
        stb += b"\x48\x8B\x82" + struct.pack("<i", off)
        stb += b"\x48\x89\x05" + struct.pack("<i", 0)
    # jmp PASS
    jmp_pos = len(stb)
    stb += b"\xEB\x00"
    pass_start = len(stb)
    stb += HIT_ORIG
    stb += b"\x48\xB8" + struct.pack("<Q", cont) + b"\xFF\xE0"
    # 填充并放置 flag / 值
    while len(stb) < STUB_FLAG:
        stb.append(0xCC)
    stb.append(0)  # 0xC0 flag
    while len(stb) < STUB_VALS:
        stb.append(0xCC)
    stb += b"\x00" * (8 * len(RECORD_OFFSETS))  # 值区 0xC8.. 
    # 填 disp
    # flag: cmp 在 0x00，长度 7，next=0x07 -> disp = 0xC0-0x07
    stb[2:6] = struct.pack("<i", STUB_FLAG - 7)
    # je: 在 je_pos，长度 2，next=je_pos+2 -> disp = pass_start-(je_pos+2)
    stb[je_pos + 1] = (pass_start - (je_pos + 2)) & 0xFF
    # 计数器 disp: inc 在 cnt_pos，长度 6，next=cnt_pos+6
    stb[cnt_pos + 2:cnt_pos + 6] = struct.pack("<i", STUB_CNT - (cnt_pos + 6))
    # 记录 disp: mov [rip+..] 在 rec_starts[i]+7，长度 7，next=rec_starts[i]+14
    for i, rs in enumerate(rec_starts):
        val_addr = STUB_VALS + 8 * i
        next_ip = rs + 14
        stb[rs + 10:rs + 14] = struct.pack("<i", val_addr - next_ip)
    # jmp: 在 jmp_pos，长度 2，next=jmp_pos+2 -> disp = pass_start-(jmp_pos+2)
    stb[jmp_pos + 1] = (pass_start - (jmp_pos + 2)) & 0xFF
    ctypes.memmove(page, bytes(stb), len(stb))
    ctypes.c_ubyte.from_address(page + STUB_FLAG).value = 0
    # 入口补丁用 rax（不碰 r11），22 字节
    patch = b"\x48\xB8" + struct.pack("<Q", page) + b"\xFF\xE0" + b"\x90" * 10
    if not _write_bytes(addr, patch):
        _dlog("install FAIL patch")
        return False
    _hit.update(addr=addr, stub=page, active=True)
    _dlog("HIT hook OK addr=%#x stub=%#x" % (addr, page))
    return True


def _hit_set_record(on: bool) -> None:
    if _hit["active"]:
        ctypes.c_ubyte.from_address(_hit["stub"] + STUB_FLAG).value = 1 if on else 0


def _hit_value() -> int:
    if not _hit["active"]:
        return 0
    return ctypes.c_uint64.from_address(_hit["stub"] + STUB_VALS + 8 * 1).value  # +0xa0


def _hit_fields() -> dict:
    out = {}
    if _hit["active"]:
        for i, off in enumerate(RECORD_OFFSETS):
            out[off] = ctypes.c_uint64.from_address(
                _hit["stub"] + STUB_VALS + 8 * i).value
    return out


def _hit_count() -> int:
    if not _hit["active"]:
        return 0
    return ctypes.c_uint32.from_address(_hit["stub"] + STUB_CNT).value


# ---------------- 窗口子类 + 显示 ----------------

_hwnd = None
_last_disp = 0.0
_last_sample = 0.0
_last_move_log = 0.0
_test_done = False
_test_log = ""
_start_time = 0.0
_cal = (1.0, 0.0, 1.0, 0.0)


def _sample_pixol(tag: str) -> None:
    """采样一次坐标/HIT/pixol 并写日志（节流）。"""
    global _last_sample
    now = time.monotonic()
    if now - _last_sample < 0.1:
        return
    _last_sample = now
    try:
        import zbrush.commands as zbc

        px, py = zbc.get_mouse_pos(global_coordinates=False)
        mat = float(zbc.pixol_pick(5, px, py))
        nx = float(zbc.pixol_pick(6, px, py))
        ny = float(zbc.pixol_pick(7, px, py))
        nz = float(zbc.pixol_pick(8, px, py))
        kind = 1 if (mat != 0.0 or nx != 0.0 or ny != 0.0 or nz != 0.0) else 0
        f = _hit_fields()
        fstr = " ".join("+%03x=%#x" % (k, v) for k, v in f.items())
        _dlog("%s L=1 pos=(%.0f,%.0f) mat=%g n=(%.3f,%.3f,%.3f) kind=%d cnt=%d | %s"
              % (tag, px, py, mat, nx, ny, nz, kind, _hit_count(), fstr))
    except Exception as e:
        _dlog("%s sample err %r" % (tag, e))


def _log_test(line: str) -> None:
    global _test_log
    _test_log += line + "\n"
    _dlog(line)


def _setup_scene() -> bool:
    try:
        import zbrush.commands as zbc

        # 探测按钮路径
        probe = [
            "Tool:MakePolyMesh3D",
            "Tool:Make PolyMesh3D",
            "Tool:Edit",
            "Document:New Document",
            "Document:New",
            "Tool:Sphere3D",
        ]
        for pth in probe:
            try:
                _log_test("exists %s = %s" % (pth, zbc.exists(pth)))
            except Exception as e:
                _log_test("exists %s ERR %r" % (pth, e))
        n = int(zbc.get_tool_count())
        idx = -1
        for i in range(n):
            p = str(zbc.get_tool_path(i) or "")
            if "Sphere3D" in p:
                idx = i
                break
        if idx < 0:
            _log_test("FAIL Sphere3D not found, tools=%d" % n)
            return False
        zbc.select_tool(idx)
        _log_test("select tool idx=%d" % idx)
        time.sleep(0.5)
        made = False
        for pth in ("Tool:Make PolyMesh3D", "Tool:MakePolyMesh3D"):
            if zbc.exists(pth):
                zbc.press(pth)
                _log_test("pressed %s" % pth)
                made = True
                break
        if not made:
            _log_test("no MakePolyMesh button found")
            return False
        time.sleep(0.8)
        # 进入 Edit 模式（开关路径 Transform:Edit）
        try:
            zbc.set("Transform:Edit", 1.0)
            _log_test("set Transform:Edit=1")
        except Exception as e:
            _log_test("set Edit err %r" % (e,))
        time.sleep(0.5)
        # 校验模型是否创建成功
        try:
            _log_test("after-create Transform:Edit=%s subtools=%s"
                      % (zbc.get("Transform:Edit"),
                         zbc.get("Tool:Subtool:SubTool Count")))
        except Exception as e:
            _log_test("verify err %r" % (e,))
        # 锁定相机，拖拽时视图不动，坐标稳定
        zbc.set("Draw:Lock Camera", 1.0)
        _log_test("scene ready (sphere + edit + lock)")
        return True
    except Exception as e:
        _log_test("scene setup err %r" % (e,))
        return False


def _canvas_at_screen(sx: int, sy: int):
    """把光标移到屏幕坐标，返回画布坐标。"""
    user32.SetCursorPos(sx, sy)
    time.sleep(0.08)
    try:
        import zbrush.commands as zbc
        return zbc.get_mouse_pos(global_coordinates=False)
    except Exception:
        return (0.0, 0.0)


def _calibrate() -> bool:
    """用窗口四角采样校准 屏幕<->画布 仿射映射。"""
    global _cal
    rect = wintypes.RECT()
    if not user32.GetWindowRect(_hwnd, ctypes.byref(rect)):
        _log_test("GetWindowRect FAIL")
        return False
    wl, wt, wr, wb = rect.left, rect.top, rect.right, rect.bottom
    pts = [
        (wl + 120, wt + 120),
        (wr - 120, wt + 120),
        (wl + 120, wb - 120),
    ]
    samples = []
    for sx, sy in pts:
        cx, cy = _canvas_at_screen(sx, sy)
        samples.append((sx, sy, cx, cy))
    # 仿射：canvas_x = ax*sx + bx; canvas_y = ay*sy + by
    (sx0, sy0, cx0, cy0) = samples[0]
    (sx1, sy1, cx1, cy1) = samples[1]
    (sx2, sy2, cx2, cy2) = samples[2]
    try:
        ax = (cx1 - cx0) / (sx1 - sx0)
        bx = cx0 - ax * sx0
        ay = (cy2 - cy0) / (sy2 - sy0)
        by = cy0 - ay * sy0
    except Exception:
        return False
    _cal = (ax, bx, ay, by)
    _log_test("cal ax=%g bx=%g ay=%g by=%g" % (ax, bx, ay, by))
    return True


def _canvas_to_screen(cx: float, cy: float):
    ax, bx, ay, by = _cal
    return int((cx - bx) / ax), int((cy - by) / ay)


def _scan_model():
    """不按左键，用 pixol 扫描画布，找出模型包围盒（画布坐标）。"""
    try:
        import zbrush.commands as zbc
        doc_w = float(zbc.get("Document:Width"))
        doc_h = float(zbc.get("Document:Height"))
        # 采样几个参考点了解画布状态
        refs = [(10, 10), (doc_w / 2, doc_h / 2), (doc_w - 10, doc_h - 10),
                (doc_w / 4, doc_h / 4), (doc_w * 3 / 4, doc_h * 3 / 4)]
        for rx, ry in refs:
            try:
                _log_test("ref pos=(%.0f,%.0f) mat=%s nz=%s"
                          % (rx, ry, zbc.pixol_pick(5, rx, ry),
                             zbc.pixol_pick(8, rx, ry)))
            except Exception as e:
                _log_test("ref err %r" % (e,))
    except Exception:
        return None
    minx, miny, maxx, maxy = doc_w, doc_h, 0, 0
    step = 40
    for y in range(0, int(doc_h), step):
        for x in range(0, int(doc_w), step):
            try:
                mat = float(zbc.pixol_pick(5, x, y))
            except Exception:
                continue
            if mat != 0.0:
                minx = min(minx, x)
                miny = min(miny, y)
                maxx = max(maxx, x)
                maxy = max(maxy, y)
    box = (minx, miny, maxx, maxy)
    _log_test("model box canvas=(%d,%d)-(%d,%d) doc=%dx%d"
              % (minx, miny, maxx, maxy, int(doc_w), int(doc_h)))
    return box


def _mouse_move_to(cx: float, cy: float, steps: int = 1):
    sx, sy = _canvas_to_screen(cx, cy)
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    dx0, dy0 = p.x, p.y
    for i in range(1, steps + 1):
        user32.SetCursorPos(
            dx0 + (sx - dx0) * i // steps,
            dy0 + (sy - dy0) * i // steps,
        )
        time.sleep(0.02)


def _run_drag_test(box):
    """模拟：空白按下 -> 拖到模型中心 -> 停 1 秒 -> 松开。"""
    minx, miny, maxx, maxy = box
    start_c = (max(minx - 150, 40), (miny + maxy) // 2)
    end_c = ((minx + maxx) // 2, (miny + maxy) // 2)
    _log_test("drag start=%s end=%s" % (start_c, end_c))
    sx, sy = _canvas_to_screen(start_c[0], start_c[1])
    user32.SetCursorPos(sx, sy)
    time.sleep(0.2)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(0.15)
    # 分段拖到模型中心，每段采样
    n = 16
    for i in range(1, n + 1):
        cx = start_c[0] + (end_c[0] - start_c[0]) * i / n
        cy = start_c[1] + (end_c[1] - start_c[1]) * i / n
        sxx, syy = _canvas_to_screen(cx, cy)
        user32.SetCursorPos(sxx, syy)
        time.sleep(0.05)
        _sample_pixol("drag")
    time.sleep(1.0)
    _sample_pixol("hold")
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
    time.sleep(0.3)
    _log_test("drag done")


def _run_auto_test() -> None:
    global _test_done
    if _test_done:
        return
    if not _hwnd:
        return
    _log_test("auto test start")
    if not _setup_scene():
        _test_done = True
        return
    if not _calibrate():
        _test_done = True
        return
    _zoom_out()
    if not _calibrate():
        _test_done = True
        return
    box = _scan_model()
    if not box or box[2] <= box[0]:
        _log_test("model scan FAIL")
        _test_done = True
        return
    _run_drag_test(box)
    # 再测一次：直接按在模型上（对照）
    cx = (box[0] + box[2]) // 2
    cy = (box[1] + box[3]) // 2
    sx, sy = _canvas_to_screen(cx, cy)
    user32.SetCursorPos(sx, sy)
    time.sleep(0.2)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, None)
    time.sleep(0.8)
    _sample_pixol("model-press")
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, None)
    time.sleep(0.3)
    _test_done = True
    _log_test("auto test DONE")


def _zoom_out() -> None:
    """滚轮向下缩小视图，让模型不占满画布。"""
    try:
        import zbrush.commands as zbc
        doc_w = float(zbc.get("Document:Width"))
        doc_h = float(zbc.get("Document:Height"))
        sx, sy = _canvas_to_screen(doc_w / 2.0, doc_h / 2.0)
        user32.SetCursorPos(sx, sy)
        time.sleep(0.3)
        for _ in range(5):
            user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -120, None)
            time.sleep(0.25)
        _log_test("zoom out done")
        time.sleep(0.5)
    except Exception as e:
        _log_test("zoom out err %r" % (e,))


def _update_display() -> None:
    global _last_disp
    now = time.monotonic()
    if now - _last_disp < 0.15:
        return
    _last_disp = now
    v = _hit_value()
    left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    txt = "HIT=%d L=%d" % (1 if v else 0, int(left))
    try:
        import zbrush.commands as zbc
        zbc.set_notebar_text(txt)
    except Exception:
        pass
    if left:
        _dlog("left=1 HIT=0x%x" % v)


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    try:
        if msg == WM_LBUTTONDOWN:
            _hit_set_record(True)
        elif msg == WM_LBUTTONUP:
            _hit_set_record(False)
        elif msg == WM_TIMER and wparam == TIMER_ID:
            left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            _hit_set_record(left)
            if left:
                _sample_pixol("timer")
            _update_display()
            if not _test_done and time.monotonic() > _start_time + 4:
                _run_auto_test()
            return 0
        elif msg == 0x0200:  # WM_MOUSEMOVE
            left = bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
            if left:
                now = time.monotonic()
                if now - _last_move_log >= 0.05:
                    _last_move_log = now
                    px = lparam & 0xFFFF
                    py = (lparam >> 16) & 0xFFFF
                    _dlog("MOVE pos=(%d,%d) L=1" % (px, py))
                _sample_pixol("move")
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


_subclass_callback = _subclass_proc
_enum_result: list = [None]


@WNDENUMPROC
def _enum_find_zbrush(hwnd, lparam) -> bool:
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


_enum_callback = _enum_find_zbrush


def _find_window():
    _enum_result[0] = None
    try:
        user32.EnumWindows(_enum_find_zbrush, 0)
    except Exception:
        pass
    return _enum_result[0]


def main() -> None:
    global _hwnd, _start_time, _cal
    _cal = (1.0, 0.0, 1.0, 0.0)
    _start_time = time.monotonic()
    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr auto test ===\n")
    except Exception:
        pass
    _dlog("main start")
    if _hit_install():
        hwnd = _find_window()
        for _ in range(20):
            if hwnd:
                break
            time.sleep(0.5)
            hwnd = _find_window()
        _hwnd = hwnd
        if hwnd:
            comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0)
            user32.SetTimer(hwnd, TIMER_ID, 50, None)
            _dlog("ready hwnd=%s" % (hwnd,))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
