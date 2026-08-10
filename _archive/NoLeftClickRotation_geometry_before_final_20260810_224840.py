# -*- coding: utf-8 -*-
"""NoLeftClickRotation（禁用左键视图旋转）— 纯 Python 版（ZBrush 2026）。

工作原理：
1. 相机锁常开：插件启用期间保持 Lock Camera 开启，左键拖空白不再旋转，
   Alt+左键不再平移（用官方 toggle 切换，锁定参考点同步更新）。
2. 右键临时解锁：右键按住时 toggle 解锁，右键拖动画布照常旋转；松开后
   延迟约 1ms 再锁定（避免旋转手势未结束时锁定触发回弹），并重扫模型。
3. 模型包围盒：空闲时用 pixol_pick（未按下时可用）扫描画布，得到模型在
   画布坐标系下的包围盒。锁相机时模型位置固定，因此拖拽中只需用光标
   画布坐标判断是否进入包围盒——不依赖 ZBrush 在交互期间被隐藏的采样。
4. 起笔桥接：空白处按下进入等待；光标进入模型包围盒后补发一次抬起清掉
   空白手势，延迟（可调）后再补发按下，ZBrush 看到全新的"按下+在模型上"
   组合，笔刷从进入点起笔。

不吞任何消息，界面按钮/滑块不受影响；Ctrl+左键遮罩原样放行。
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes

DEBUG_LOG: str = os.path.join(
    os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_final.log"
)

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_TIMER = 0x0113

MK_LBUTTON = 0x0001
MK_SHIFT = 0x0004

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12

TIMER_ID = 0x4E4C5449
BRIDGE_TIMER_ID = 0x4E4C5442
SUBCLASS_ID = 0x4E525442
RELOCK_DELAY: float = 0.001

LOCK_CAMERA_PATH: str = "Draw:Lock Camera"

# 临时调试开关（验证后移除）
_DBG: bool = True


def _dlog(line: str) -> None:
    if not _DBG:
        return
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), line))
    except Exception:
        pass

ST_IDLE = 0
ST_ARMED = 1
ST_PENDING = 2
ST_STROKING = 3

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
user32.GetKeyState.restype = ctypes.c_short
user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p]
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

# ---------------- 配置 ----------------

PLUGIN_DIR: str = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH: str = os.path.join(PLUGIN_DIR, "config.txt")

_enabled: bool = True
_bridge_delay_ms: int = 0


def _read_config() -> None:
    global _enabled, _bridge_delay_ms
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if lines:
            _enabled = lines[0].strip() != "0"
        if len(lines) > 1:
            try:
                _bridge_delay_ms = max(0, min(2000, int(float(lines[1].strip()))))
            except Exception:
                _bridge_delay_ms = 0
    except Exception:
        _enabled = True
        _bridge_delay_ms = 0


def load_enabled() -> bool:
    return _enabled


def _save_config() -> None:
    try:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("1\n" if _enabled else "0\n")
            f.write("%d\n" % _bridge_delay_ms)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


def save_enabled(value: bool) -> None:
    global _enabled
    _enabled = bool(value)
    _save_config()


def save_bridge_delay(ms: int) -> None:
    global _bridge_delay_ms
    _bridge_delay_ms = max(0, min(2000, int(ms)))
    _save_config()


# ---------------- 语言与界面 ----------------


def detect_language() -> str:
    try:
        lang_id: int = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if (lang_id & 0x3FF) == 0x04:
            return "zh"
    except Exception:
        pass
    return "en"


LANG: str = detect_language()
if LANG == "zh":
    PLUGIN_NAME: str = "禁用左键视图旋转"
    SWITCH_LABEL: str = "启用"
    SWITCH_INFO: str = (
        "锁定摄像机：左键拖空白不再旋转/平移；右键按住可旋转；"
        "拖到模型上笔刷自动起笔。"
    )
    DELAY_LABEL: str = "桥接延迟 ms"
    DELAY_INFO: str = "清空手势后等待该时长再补发按下（0=立即）"
else:
    PLUGIN_NAME = "Disable Left-Button View Rotation"
    SWITCH_LABEL = "Enable"
    SWITCH_INFO = (
        "Keeps the camera locked: left-drag on blank canvas won't rotate or pan; "
        "hold the right button to rotate; strokes start when the cursor hits the mesh."
    )
    DELAY_LABEL = "Bridge delay ms"
    DELAY_INFO = "Wait before re-pressing after clearing the gesture (0=immediate)"

PALETTE: str = "Zplugin:" + PLUGIN_NAME
BODY: str = PALETTE + ":Body"
SWITCH_PATH: str = BODY + ":" + SWITCH_LABEL
DELAY_PATH: str = BODY + ":" + DELAY_LABEL


def on_toggle(sender: str, value: bool) -> None:
    save_enabled(bool(value))
    if not value:
        _restore_camera()
        _reset_state()


def on_delay_change(sender: str, value: float) -> None:
    save_bridge_delay(int(value))


def setup_ui() -> None:
    import zbrush.commands as zbc

    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)
    state: bool = load_enabled()
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(SWITCH_PATH, state, SWITCH_INFO, on_toggle,
                   initially_disabled=False, width=1.0)
    zbc.add_slider(DELAY_PATH, float(_bridge_delay_ms), 5, 0.0, 500.0,
                   DELAY_INFO, on_delay_change, width=1.0)


# ---------------- 相机锁 ----------------

_right_down_state: bool = False
_right_up_time: float = 0.0


def _get_lock_state() -> bool:
    import zbrush.commands as zbc
    return bool(float(zbc.get(LOCK_CAMERA_PATH)))


def _apply_lock(want: bool) -> None:
    try:
        import zbrush.commands as zbc
        if _get_lock_state() == want:
            return
        try:
            zbc.toggle(LOCK_CAMERA_PATH)
        except Exception:
            pass
        if _get_lock_state() != want:
            try:
                zbc.set(LOCK_CAMERA_PATH, 1.0 if want else 0.0)
            except Exception:
                pass
    except Exception:
        pass


def _restore_camera() -> None:
    try:
        import zbrush.commands as zbc
        if _get_lock_state():
            try:
                zbc.toggle(LOCK_CAMERA_PATH)
            except Exception:
                zbc.set(LOCK_CAMERA_PATH, 0.0)
    except Exception:
        pass


def _right_down() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_RBUTTON) & 0x8000)
    except Exception:
        return False


def _camera_sync() -> None:
    global _right_down_state, _right_up_time
    if not load_enabled():
        return
    down = _right_down()
    if not down and _right_down_state:
        _right_up_time = time.monotonic()
    _right_down_state = down
    if down:
        _right_up_time = 0.0
        _apply_lock(False)
    elif _right_up_time == 0.0 or time.monotonic() - _right_up_time >= RELOCK_DELAY:
        _right_up_time = 0.0
        _apply_lock(True)
        _rescan_box()


# ---------------- 模型包围盒 ----------------

_box = None
_last_scan = 0.0


def _in_box(cx: float, cy: float) -> bool:
    if not _box:
        return False
    minx, miny, maxx, maxy = _box
    return minx <= cx <= maxx and miny <= cy <= maxy


def _rescan_box() -> None:
    global _box, _last_scan
    now = time.monotonic()
    if now - _last_scan < 2.0:
        return
    _last_scan = now
    try:
        import zbrush.commands as zbc
        if not bool(zbc.get("Transform:Edit")):
            return
        doc_w = float(zbc.get("Document:Width"))
        doc_h = float(zbc.get("Document:Height"))
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
        if maxx > minx and maxy > miny:
            _box = (minx, miny, maxx, maxy)
    except Exception:
        pass


# ---------------- 状态机 ----------------

_state: int = ST_IDLE
_mesh_hits: int = 0
_hwnd = None
_bridge_lparam: int = 0
_bridge_up_consumed: bool = False


def _button_flags() -> int:
    flags: int = MK_LBUTTON
    if user32.GetKeyState(VK_SHIFT) & 0x8000:
        flags |= MK_SHIFT
    return flags


def _real_left_down() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    except Exception:
        return False


def _bridge_fire_down(hwnd) -> None:
    global _state
    _state = ST_STROKING
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, _button_flags(), _bridge_lparam)
    _dlog("bridge DOWN posted -> STROKING")


def _cancel_bridge(hwnd) -> None:
    global _state, _mesh_hits, _bridge_up_consumed
    user32.KillTimer(hwnd, BRIDGE_TIMER_ID)
    _state = ST_IDLE
    _mesh_hits = 0
    _bridge_up_consumed = False


def _reset_state() -> None:
    global _state, _mesh_hits
    _state = ST_IDLE
    _mesh_hits = 0


def _cursor_canvas():
    try:
        import zbrush.commands as zbc
        return zbc.get_mouse_pos(global_coordinates=False)
    except Exception:
        return (None, None)


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    global _state, _mesh_hits, _bridge_lparam, _bridge_up_consumed
    try:
        if msg == WM_RBUTTONDOWN or msg == WM_RBUTTONUP:
            global _right_down_state, _right_up_time
            if msg == WM_RBUTTONDOWN:
                _right_down_state = True
                _right_up_time = 0.0
            else:
                _right_down_state = False
                _right_up_time = time.monotonic()
            if load_enabled():
                _camera_sync()
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if msg == WM_TIMER and wparam == BRIDGE_TIMER_ID:
            user32.KillTimer(hwnd, BRIDGE_TIMER_ID)
            if _state == ST_PENDING and load_enabled() and _real_left_down():
                _bridge_fire_down(hwnd)
            else:
                _cancel_bridge(hwnd)
            return 0

        if msg == WM_TIMER and wparam == TIMER_ID:
            if not _real_left_down() and _state != ST_IDLE:
                prev = _state
                _state = ST_IDLE
                _mesh_hits = 0
                user32.KillTimer(hwnd, BRIDGE_TIMER_ID)
                _bridge_up_consumed = False
                if prev == ST_STROKING:
                    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, _bridge_lparam)
            if load_enabled():
                _camera_sync()
            return 0

        if msg not in (WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if not load_enabled():
            _reset_state()
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if (_state != ST_IDLE and msg not in (WM_LBUTTONUP, WM_LBUTTONDBLCLK)
                and not _real_left_down()):
            _state = ST_IDLE
            _mesh_hits = 0
            user32.KillTimer(hwnd, BRIDGE_TIMER_ID)
            _bridge_up_consumed = False

        if _state == ST_ARMED:
            if msg == WM_MOUSEMOVE:
                px, py = _cursor_canvas()
                if px is not None and _in_box(px, py):
                    _mesh_hits += 1
                    if _mesh_hits >= 2:
                        _mesh_hits = 0
                        _state = ST_PENDING
                        _bridge_lparam = lparam
                        _bridge_up_consumed = False
                        user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)
                        if _bridge_delay_ms > 0:
                            user32.SetTimer(hwnd, BRIDGE_TIMER_ID, _bridge_delay_ms, None)
                        else:
                            _bridge_fire_down(hwnd)
                else:
                    _mesh_hits = 0
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            if msg in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                _reset_state()
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        elif _state == ST_PENDING:
            if msg == WM_MOUSEMOVE:
                _bridge_lparam = lparam
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            if msg == WM_LBUTTONUP:
                if not _bridge_up_consumed:
                    _bridge_up_consumed = True
                    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
                _cancel_bridge(hwnd)
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        elif _state == ST_STROKING:
            if msg == WM_LBUTTONUP:
                r = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
                _reset_state()
                return r
        elif msg in (WM_LBUTTONDOWN, WM_LBUTTONDBLCLK):
            if user32.GetKeyState(VK_CONTROL) & 0x8000 or user32.GetKeyState(VK_MENU) & 0x8000:
                _reset_state()
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            px, py = _cursor_canvas()
            if px is not None and _in_box(px, py):
                _state = ST_STROKING
                _mesh_hits = 0
            else:
                _state = ST_ARMED
                _mesh_hits = 0
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
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
    global _enabled, _hwnd
    if not os.path.isfile(CONFIG_PATH):
        save_enabled(True)
    else:
        _read_config()
    try:
        setup_ui()
    except Exception:
        pass
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
    if load_enabled():
        _rescan_box()
        _apply_lock(True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
