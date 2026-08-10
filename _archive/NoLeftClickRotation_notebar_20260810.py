# -*- coding: utf-8 -*-
"""NoLeftClickRotation（禁用左键视图旋转）- 单文件 Python 插件（ZBrush 2026）。

原理：
1. 相机锁定：插件启用期间保持 Draw:Lock Camera 开启，左键拖空白不旋转、
   Alt+左键不平移（用官方 toggle 切换，锁定参考点同步更新）。
2. 右键临时解锁：右键按住时解锁相机，右键拖动照常旋转；松开后延迟 1ms
   重新锁定（避免旋转手势未结束时锁定触发回弹）。
3. 起笔桥接：鼠标移动时（未按下）用 pixol_pick 持续采样，记录光标最近
   是否在模型上。左键按下时：
     - 在模型上 -> 完全不干预，正常雕刻（手感无损）；
     - 在空白处 -> 高频（默认 90 次/秒）重置鼠标状态：
       同步松开 -> 采样（松开窗口内 pixol_pick 恢复真实值）-> 按当前坐标
       重新按下。一旦采样到光标已进入模型，重新按下即被判定为"在模型上
       按下"，起笔雕刻，随即停手完全不干预。
   桥接只发生在"空白按下"的拖拽中，Ctrl+左键遮罩、Alt+左键平移原样放行。
4. 不吞任何消息，界面按钮/滑块不受影响。
"""

import ctypes
import os
import time
from ctypes import wintypes

DEBUG_LOG: str = os.path.join(
    os.environ.get("TEMP", r"C:\Users\liuwenbo\AppData\Local\Temp"), "nlr_debug.log"
)


def _dlog(line: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S.%f")[:-3], line))
    except Exception:
        pass

# ---------------- 窗口常量 ----------------

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_TIMER = 0x0113

MK_LBUTTON = 0x0001

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CONTROL = 0x11
VK_MENU = 0x12

SUBCLASS_ID = 0x4E4C524E
SAMPLE_TIMER_ID = 0x4E4C5253
BRIDGE_TIMER_ID = 0x4E4C5242

RELOCK_DELAY: float = 0.001
SAMPLE_INTERVAL: float = 0.04

ST_IDLE = 0
ST_STROKING = 1
ST_BRIDGING = 2

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

user32 = ctypes.WinDLL("user32")
comctl32 = ctypes.WinDLL("comctl32")

SubclassProcType = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p,
)
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
]
user32.SetTimer.restype = ctypes.c_void_p
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_void_p, wintypes.UINT, ctypes.c_void_p]
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_void_p]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]

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
_bridge_hz: int = 90


def _read_config() -> None:
    global _enabled, _bridge_hz
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if lines:
            _enabled = lines[0].strip() != "0"
        if len(lines) > 1:
            try:
                _bridge_hz = max(30, min(200, int(float(lines[1].strip()))))
            except Exception:
                _bridge_hz = 90
    except Exception:
        _enabled = True
        _bridge_hz = 90


def _save_config() -> None:
    try:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("1\n" if _enabled else "0\n")
            f.write("%d\n" % _bridge_hz)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


def load_enabled() -> bool:
    return _enabled


def save_enabled(value: bool) -> None:
    global _enabled
    _enabled = bool(value)
    _save_config()


def save_bridge_hz(hz: int) -> None:
    global _bridge_hz
    _bridge_hz = max(30, min(200, int(hz)))
    _save_config()


def _bridge_interval_ms() -> int:
    return max(1, int(round(1000.0 / _bridge_hz)))


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
        "锁定相机：左键拖空白不旋转、Alt+左键不平移；"
        "右键按住可旋转；空白拖到模型上自动接笔雕刻。"
    )
    HZ_LABEL: str = "桥接频率 Hz"
    HZ_INFO: str = "空白拖拽时每秒重置检测次数（默认 90）"
else:
    PLUGIN_NAME = "Disable Left-Button View Rotation"
    SWITCH_LABEL = "Enable"
    SWITCH_INFO = (
        "Camera stays locked: left-drag on blank canvas won't rotate or pan; "
        "hold the right button to rotate; strokes start automatically when "
        "dragging from blank onto the mesh."
    )
    HZ_LABEL = "Bridge frequency Hz"
    HZ_INFO = "Reset/check rate per second while dragging on blank (default 90)"

PALETTE: str = "Zplugin:" + PLUGIN_NAME
BODY: str = PALETTE + ":Body"
SWITCH_PATH: str = BODY + ":" + SWITCH_LABEL
HZ_PATH: str = BODY + ":" + HZ_LABEL


def on_toggle(sender: str, value: bool) -> None:
    save_enabled(bool(value))
    if not value:
        _reset_all()
        _restore_camera()


def on_hz(sender: str, value: float) -> None:
    save_bridge_hz(int(value))


def setup_ui() -> None:
    import zbrush.commands as zbc

    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(SWITCH_PATH, load_enabled(), SWITCH_INFO, on_toggle,
                   initially_disabled=False, width=1.0)
    zbc.add_slider(HZ_PATH, float(_bridge_hz), 0, 30.0, 200.0,
                   HZ_INFO, on_hz, width=1.0)


# ---------------- 相机锁定 ----------------

LOCK_CAMERA_PATH: str = "Draw:Lock Camera"


def _get_lock_state() -> bool:
    try:
        import zbrush.commands as zbc
        return bool(float(zbc.get(LOCK_CAMERA_PATH)))
    except Exception:
        return True


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


_right_down_state: bool = False
_right_up_time: float = 0.0


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


# ---------------- 采样与桥接 ----------------

_hwnd = None
_state: int = ST_IDLE
_last_mesh: bool = False
_cur_client: tuple = (0, 0)
_synthetic_up: bool = False
_last_sample: float = 0.0


def _real_left_down() -> bool:
    try:
        return bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)
    except Exception:
        return False


def _client_xy(hwnd) -> tuple:
    pt = wintypes.POINT()
    if user32.GetCursorPos(ctypes.byref(pt)) and user32.ScreenToClient(hwnd, ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return _cur_client


def _pack_lparam(x, y) -> int:
    return (int(y) & 0xFFFF) << 16 | (int(x) & 0xFFFF)


def _sample_mesh() -> bool:
    try:
        import zbrush.commands as zbc
        x, y = zbc.get_mouse_pos(global_coordinates=False)
        mat = float(zbc.pixol_pick(5, float(x), float(y)))
        return mat != 0.0
    except Exception:
        return _last_mesh


def _sample_mat():
    try:
        import zbrush.commands as zbc
        x, y = zbc.get_mouse_pos(global_coordinates=False)
        mat = float(zbc.pixol_pick(5, float(x), float(y)))
        return mat
    except Exception as e:
        return repr(e)


_last_shown: str = ""
_last_show_t: float = 0.0


def _show_status(mat=None) -> None:
    """Print pixol_pick value + state as text in the ZBrush top bar."""
    global _last_shown, _last_show_t
    try:
        m = _sample_mat() if mat is None else mat
        m_txt = ("%.1f" % m) if isinstance(m, float) else "err"
        state_txt = ("idle", "stroke", "bridge")[_state] if 0 <= _state <= 2 else "?"
        txt = "NLC mat=%s %s" % (m_txt, state_txt)
        now = time.monotonic()
        if txt == _last_shown and now - _last_show_t < 0.1:
            return
        _last_shown = txt
        _last_show_t = now
        import zbrush.commands as zbc
        zbc.set_notebar_text(txt)
    except Exception:
        pass


def _sample_tick() -> None:
    global _last_mesh, _last_sample
    if not load_enabled() or _real_left_down():
        return
    now = time.monotonic()
    if now - _last_sample < SAMPLE_INTERVAL:
        return
    _last_sample = now
    _last_mesh = _sample_mesh()


def _reset_all() -> None:
    global _state, _synthetic_up
    _state = ST_IDLE
    _synthetic_up = False
    if _hwnd:
        user32.KillTimer(_hwnd, BRIDGE_TIMER_ID)


def _bridge_tick(hwnd) -> None:
    """One reset cycle: sync release -> sample -> re-press at current coords."""
    global _last_mesh, _synthetic_up
    x, y = _client_xy(hwnd)
    _cur_client = (x, y)
    lp = _pack_lparam(x, y)
    _synthetic_up = True
    user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lp)
    mat = _sample_mat()
    _last_mesh = (mat != 0.0) if isinstance(mat, float) else _last_mesh
    _dlog("BRIDGE xy=(%d,%d) mat=%s mesh=%s" % (x, y, mat, _last_mesh))
    _show_status(mat)
    user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lp)


def _handle_message(hwnd, msg, wparam, lparam) -> int:
    global _state, _cur_client, _synthetic_up
    try:
        if msg == WM_TIMER and wparam == SAMPLE_TIMER_ID:
            _camera_sync()
            _sample_tick()
            _show_status()
            return 0

        if msg == WM_TIMER and wparam == BRIDGE_TIMER_ID:
            if _state == ST_BRIDGING and _real_left_down():
                _bridge_tick(hwnd)
            else:
                _state = ST_IDLE
            return 0

        if msg == WM_LBUTTONDOWN:
            if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000 or \
               user32.GetAsyncKeyState(VK_MENU) & 0x8000:
                _reset_all()
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            x, y = _client_xy(hwnd)
            _cur_client = (x, y)
            if not load_enabled():
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            down_mat = _sample_mat()
            down_mesh = (down_mat != 0.0) if isinstance(down_mat, float) else _last_mesh
            _dlog("DOWN xy=(%d,%d) last_mesh=%s down_mat=%s down_mesh=%s"
                  % (x, y, _last_mesh, down_mat, down_mesh))
            if down_mesh:
                _state = ST_STROKING
            else:
                _state = ST_BRIDGING
                user32.SetTimer(hwnd, BRIDGE_TIMER_ID, _bridge_interval_ms(), None)
            _dlog("STATE=%s" % ("STROKING" if _state == ST_STROKING else "BRIDGING"))
            _show_status()
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

        if msg == WM_LBUTTONUP:
            if _synthetic_up:
                _synthetic_up = False
                return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
            _reset_all()
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


def main() -> None:
    try:
        with open(DEBUG_LOG, "w", encoding="utf-8") as f:
            f.write("=== nlr debug ===\n")
    except Exception:
        pass
    _dlog("main start")
    _read_config()
    try:
        setup_ui()
    except Exception:
        pass
    hwnd = None
    for _ in range(20):
        _enum_result[0] = None
        try:
            user32.EnumWindows(_enum_find_zbrush, 0)
        except Exception:
            pass
        hwnd = _enum_result[0]
        if hwnd:
            break
        time.sleep(0.5)
    global _hwnd
    _hwnd = hwnd
    if hwnd:
        comctl32.SetWindowSubclass(hwnd, _subclass_proc, SUBCLASS_ID, 0)
        user32.SetTimer(hwnd, SAMPLE_TIMER_ID, 20, None)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
