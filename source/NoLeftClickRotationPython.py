# -*- coding: utf-8 -*-
"""No Left Click Rotation V1 for ZBrush on Windows."""

import ctypes
import os
import struct
import time
from ctypes import wintypes
from zbrush import commands as zbc

VERSION = "1.0.0"

WM_TIMER = 0x0113
WM_CANCELMODE = 0x001F
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_CAPTURECHANGED = 0x0215
WM_NCDESTROY = 0x0082

MK_LBUTTON = 0x0001
MK_SHIFT = 0x0004
MK_CONTROL = 0x0008
MK_MBUTTON = 0x0010
MK_RBUTTON = 0x0002
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_SHIFT = 0x10
VK_CONTROL = 0x11

CANVAS_WINDOW_ID = 1004
WINDOW_ID_PATH = "Preferences:Utilities:View Window Id"
EDIT_PATH = "Transform:Edit"
LOCK_CAMERA_PATH = "Draw:Lock Camera"

def _system_language_is_chinese():
    """Use the Windows UI language; unsupported languages fall back to English."""
    try:
        get_language = ctypes.windll.kernel32.GetUserDefaultUILanguage
        get_language.restype = wintypes.WORD
        return (int(get_language()) & 0x03FF) == 0x0004
    except Exception:
        return False


_TEXT_EN = {
    "palette": "No Left Click Rotation",
    "enable": "Enable",
    "enable_info": "Enable the plugin",
    "camera_lock": "Camera Lock",
    "camera_lock_info": "Enable the camera lock",
    "bili": "BiliBli",
    "bili_info": "By神说要凑数，Open the author’s BiliBili page",
    "github": "GitHub",
    "github_info": "Open the project on GitHub",
}
_TEXT_ZH = {
    "palette": "禁用左键导航",
    "enable": "启用",
    "enable_info": "启用插件",
    "camera_lock": "锁定相机",
    "camera_lock_info": "启用相机锁定",
    "bili": "哔哩哔哩",
    "bili_info": "By神说要凑数，点击打开作者的哔哩哔哩主页",
    "github": "GitHub",
    "github_info": "打开项目的 GitHub 页面",
}
UI_TEXT = _TEXT_ZH if _system_language_is_chinese() else _TEXT_EN

ENGLISH_PALETTE = "Zplugin:No Left Click Rotation"
CHINESE_PALETTE = "Zplugin:禁用左键导航"
PALETTE = "Zplugin:" + UI_TEXT["palette"]
# Close either localized palette left by an earlier run. BODY is the old V1
# subpalette used by pre-stable builds.
LEGACY_PALETTES = (ENGLISH_PALETTE, CHINESE_PALETTE)
BODY = ENGLISH_PALETTE + ":V1"
ENABLE_PATH = PALETTE + ":" + UI_TEXT["enable"]
CAM_LOCK_PATH = PALETTE + ":" + UI_TEXT["camera_lock"]
BILI_PATH = PALETTE + ":" + UI_TEXT["bili"]
GITHUB_PATH = PALETTE + ":" + UI_TEXT["github"]

IDLE = 0
UI_PASS = 1
MODEL_PASS = 2
CLASSIFY = 3
LIGHTBOX_PASS = 4
WAIT_MODEL = 5
START_PENDING = 6
SCULPTING = 7

POLL_TIMER = 0x4E4C5631
CLASSIFY_TIMER = 0x4E4C5632
START_TIMER = 0x4E4C5633
SUBCLASS_ID = 0x4E4C4352
POLL_MS = 5
CLASSIFY_MS = 5
START_DELAY_MS = 1
RIGHT_RELOCK_MS = 2

# Numeric resource IDs of the standard Windows system cursors. The IDC_*
# macros expand to pointer-typed values, so plain integers are used here.
SYSTEM_CURSOR_IDS = (
    32512,  # IDC_ARROW
    32513,  # IDC_IBEAM
    32514,  # IDC_WAIT
    32515,  # IDC_CROSS
    32516,  # IDC_UPARROW
    32642,  # IDC_SIZENWSE
    32643,  # IDC_SIZENESW
    32644,  # IDC_SIZEWE
    32645,  # IDC_SIZENS
    32646,  # IDC_SIZEALL
    32648,  # IDC_NO
    32649,  # IDC_HAND
    32650,  # IDC_APPSTARTING
    32651,  # IDC_HELP
)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
SubclassProc = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM,
    ctypes.c_void_p, ctypes.c_void_p,
)
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
SetCursorProc = ctypes.WINFUNCTYPE(wintypes.HANDLE, wintypes.HANDLE)

user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetCursor.restype = wintypes.HANDLE
user32.LoadCursorW.restype = wintypes.HANDLE
user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.EnumWindows.argtypes = [EnumProc, wintypes.LPARAM]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                            ctypes.POINTER(wintypes.DWORD)]
user32.SetTimer.restype = ctypes.c_size_t
user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t,
                            wintypes.UINT, ctypes.c_void_p]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [wintypes.HWND, SubclassProc,
                                       ctypes.c_size_t, ctypes.c_size_t]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT,
                                     WPARAM, LPARAM]
comctl32.RemoveWindowSubclass.argtypes = [wintypes.HWND, SubclassProc,
                                          ctypes.c_size_t]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]

_hwnd = 0
_enabled = True
_camera_lock = True
_state = IDLE
_injecting = False
_system_cursor_seen = False
_system_cursors = []
_down_cursor = 0
_set_cursor_slot = 0
_set_cursor_address = 0
_set_cursor_original = None
_set_cursor_callback = None
_cursor_callback_keepalive = []
_right_relock_at = 0.0
_hover_mat = None
_hover_ready = False
_hover_mat_at = 0.0
_installed = False
_lock_state = None
_lock_assert_at = 0.0
_edit_cache = None
_edit_cache_at = 0.0

def _key(vkey):
    return bool(user32.GetAsyncKeyState(vkey) & 0x8000)


def _get_switch(path, default=False):
    try:
        return bool(zbc.exists(path) and float(zbc.get(path)))
    except Exception:
        return default


def _set_switch(path, value):
    try:
        if _get_switch(path) == bool(value):
            return
        try:
            zbc.set(path, float(bool(value)))
        except Exception:
            zbc.toggle(path)
    except Exception:
        pass


def _edit_mode():
    return _get_switch(EDIT_PATH)


def _active():
    return _enabled and _edit_mode()


def _window_id():
    try:
        return int(round(float(zbc.get(WINDOW_ID_PATH))))
    except Exception:
        return -1


def _window_id_path_works():
    try:
        float(zbc.get(WINDOW_ID_PATH))
        return True
    except Exception:
        return False


def _mat():
    try:
        x, y = zbc.get_mouse_pos(global_coordinates=False)
        return float(zbc.pixol_pick(5, float(x), float(y)))
    except Exception:
        return 0.0


def _lparam(hwnd):
    x, y = _client_point(hwnd)
    return ((y & 0xffff) << 16) | (x & 0xffff)


def _client_point(hwnd):
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        return (0, 0)
    if not user32.ScreenToClient(hwnd, ctypes.byref(point)):
        return (0, 0)
    return (int(point.x), int(point.y))


def _mods():
    value = 0
    if _key(VK_SHIFT):
        value |= MK_SHIFT
    if _key(VK_CONTROL):
        value |= MK_CONTROL
    return value


def _send(hwnd, message, wparam):
    global _injecting
    _injecting = True
    try:
        return user32.SendMessageW(hwnd, message, wparam, _lparam(hwnd))
    finally:
        _injecting = False


def _write_pointer(slot, value):
    old = wintypes.DWORD()
    if not kernel32.VirtualProtect(ctypes.c_void_p(slot), 8, 0x04,
                                   ctypes.byref(old)):
        return False
    ctypes.c_uint64.from_address(slot).value = int(value)
    unused = wintypes.DWORD()
    kernel32.VirtualProtect(ctypes.c_void_p(slot), 8, old.value,
                            ctypes.byref(unused))
    return True


def _find_set_cursor_slot():
    module = int(kernel32.GetModuleHandleW(None) or 0)
    header = ctypes.string_at(module, 0x1000)
    pe = struct.unpack_from("<I", header, 0x3C)[0]
    optional = ctypes.string_at(module + pe + 24, 0x200)
    import_rva = struct.unpack_from("<I", optional, 120)[0]
    descriptor = module + import_rva
    while True:
        original, _, _, name_rva, first = struct.unpack(
            "<IIIII", ctypes.string_at(descriptor, 20))
        if not any((original, name_rva, first)):
            break
        dll = ctypes.string_at(module + name_rva).decode("ascii", "replace")
        if dll.casefold() == "user32.dll":
            lookup = module + (original or first)
            index = 0
            while True:
                entry = ctypes.c_uint64.from_address(lookup + index * 8).value
                if not entry:
                    break
                if not entry >> 63:
                    name = ctypes.string_at(module + entry + 2).decode(
                        "ascii", "replace")
                    if name == "SetCursor":
                        return module + first + index * 8
                index += 1
        descriptor += 20
    return 0


def _is_system_cursor(cursor):
    return cursor in _system_cursors


def _install_cursor_watch():
    global _set_cursor_slot, _set_cursor_address, _set_cursor_original
    global _set_cursor_callback, _system_cursors, _system_cursor_seen
    _set_cursor_slot = _find_set_cursor_slot()
    if not _set_cursor_slot:
        return False
    _set_cursor_address = ctypes.c_uint64.from_address(_set_cursor_slot).value
    _set_cursor_original = SetCursorProc(_set_cursor_address)
    _system_cursors = [
        int(user32.LoadCursorW(None, ctypes.c_void_p(cursor_id)) or 0)
        for cursor_id in SYSTEM_CURSOR_IDS
    ]

    @SetCursorProc
    def callback(cursor):
        global _system_cursor_seen
        # Any Windows system cursor (arrow, I-beam, hand, resize, ...) means
        # ZBrush handed the cursor back to the OS, i.e. we are over LightBox
        # or some native UI surface rather than the sculpting canvas.
        if _state == CLASSIFY and _is_system_cursor(int(cursor or 0)):
            _system_cursor_seen = True
        return _set_cursor_original(cursor)

    _set_cursor_callback = callback
    return _write_pointer(
        _set_cursor_slot, ctypes.cast(callback, ctypes.c_void_p).value)


def _restore_cursor_watch():
    if not (_set_cursor_slot and _set_cursor_address and _set_cursor_callback):
        return
    try:
        callback_address = int(
            ctypes.cast(_set_cursor_callback, ctypes.c_void_p).value or 0)
        current_address = ctypes.c_uint64.from_address(
            _set_cursor_slot).value
        # A later hook may chain through our callback. Restore the original
        # pointer only while the IAT slot still belongs to this plugin.
        if current_address == callback_address:
            if not _write_pointer(_set_cursor_slot, _set_cursor_address):
                _cursor_callback_keepalive.append(_set_cursor_callback)
        else:
            _cursor_callback_keepalive.append(_set_cursor_callback)
    except (OSError, ValueError):
        _cursor_callback_keepalive.append(_set_cursor_callback)


def _lock_camera(value):
    _set_switch(LOCK_CAMERA_PATH, value)


def _edit_mode_cached():
    global _edit_cache, _edit_cache_at
    now = time.perf_counter()
    if now >= _edit_cache_at:
        _edit_cache = _get_switch(EDIT_PATH)
        _edit_cache_at = now + 0.1
    return _edit_cache


def _sync_camera():
    global _lock_state, _lock_assert_at
    # want = None means "leave the camera switch alone": this applies whenever
    # the plugin is disabled or the camera lock feature is off, so a disabled
    # plugin never touches the camera (all features off).
    if not (_enabled and _camera_lock):
        return
    right_held = _key(VK_RBUTTON)
    relock_grace = time.perf_counter() < _right_relock_at
    want = _edit_mode_cached() and not right_held and not relock_grace
    now = time.perf_counter()
    if want != _lock_state or now >= _lock_assert_at:
        _lock_camera(want)
        _lock_state = want
        _lock_assert_at = now + 0.2


def _sample_hover():
    global _hover_mat, _hover_mat_at, _hover_ready
    if not (_enabled and _edit_mode_cached()):
        return
    if _state != IDLE or _key(VK_LBUTTON):
        return
    if _window_id() != CANVAS_WINDOW_ID:
        return
    now = time.perf_counter()
    if now - _hover_mat_at < 0.01:
        return
    _hover_mat = _mat()
    _hover_mat_at = now
    _hover_ready = True


def _clear_timers(hwnd):
    user32.KillTimer(hwnd, CLASSIFY_TIMER)
    user32.KillTimer(hwnd, START_TIMER)


def _reset(hwnd):
    global _state
    _clear_timers(hwnd)
    if _state == WAIT_MODEL:
        _send(hwnd, WM_MBUTTONUP, _mods())
    _state = IDLE


def _begin_wait(hwnd):
    global _state
    if not _key(VK_LBUTTON):
        _state = IDLE
        return
    _state = WAIT_MODEL
    _send(hwnd, WM_MBUTTONDOWN, _mods() | MK_MBUTTON)


def _finish_classify(hwnd):
    global _state
    user32.KillTimer(hwnd, CLASSIFY_TIMER)
    if _state != CLASSIFY:
        return
    system_cursor = (
        _system_cursor_seen
        or _is_system_cursor(_down_cursor)
        or _is_system_cursor(int(user32.GetCursor() or 0))
    )
    if system_cursor:
        if _key(VK_LBUTTON):
            # The real down is still active in ZBrush: keep it, let moves flow
            # so click/drag behave naturally (no click-before-drag side
            # effect). The real up completes the gesture.
            _state = LIGHTBOX_PASS
        else:
            # Quick click: the real up already passed through during Classify.
            _state = IDLE
        return
    # Blank canvas: end the real press with a synthetic up, then enter the
    # middle-button wait (the press must not stay active on empty canvas).
    _send(hwnd, WM_LBUTTONUP, _mods())
    _begin_wait(hwnd)


def _poll_model(hwnd):
    global _state
    if _state != WAIT_MODEL:
        return
    if not _active() or not _key(VK_LBUTTON):
        _reset(hwnd)
        return
    value = _mat()
    if value == 0.0:
        return
    _send(hwnd, WM_MBUTTONUP, _mods())
    _state = START_PENDING
    user32.SetTimer(hwnd, START_TIMER, START_DELAY_MS, None)


def _start_sculpt(hwnd):
    global _state
    user32.KillTimer(hwnd, START_TIMER)
    if _state != START_PENDING:
        return
    if not _active() or not _key(VK_LBUTTON):
        _state = IDLE
        return
    _send(hwnd, WM_LBUTTONDOWN, _mods() | MK_LBUTTON)
    _send(hwnd, WM_MOUSEMOVE, _mods() | MK_LBUTTON)
    _state = SCULPTING


def _begin_left(hwnd, msg, wparam, lparam):
    global _state, _system_cursor_seen, _down_cursor
    if not _active():
        _state = IDLE
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    wid = _window_id()
    if wid != CANVAS_WINDOW_ID:
        _state = UI_PASS
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    if _hover_ready and _hover_mat != 0.0:
        _state = MODEL_PASS
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    # Ctrl keeps its native canvas gesture. Alt+left follows the same
    # UI/model/LightBox/blank classification as an ordinary left press.
    if _key(VK_CONTROL):
        _state = UI_PASS
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    # Ambiguous LightBox/blank-canvas point: pass the real down but keep it
    # active; swallow moves while classifying (so ZBrush cannot arm its
    # background-rotate gesture). The synthetic UP is deferred to the
    # classification result: LightBox keeps the press (natural click/drag),
    # blank canvas ends it before the middle-button wait.
    _down_cursor = int(user32.GetCursor() or 0)
    _system_cursor_seen = False
    _state = CLASSIFY
    result = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    user32.SetTimer(hwnd, CLASSIFY_TIMER, CLASSIFY_MS, None)
    return result


def _handle(hwnd, msg, wparam, lparam):
    global _state, _right_relock_at
    global _hwnd, _lock_state, _hover_mat, _hover_ready, _installed
    if _injecting:
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_TIMER:
        timer = int(wparam)
        if timer == POLL_TIMER:
            _sync_camera()
            _poll_model(hwnd)
            _sample_hover()
            return 0
        if timer == CLASSIFY_TIMER:
            _finish_classify(hwnd)
            return 0
        if timer == START_TIMER:
            _start_sculpt(hwnd)
            return 0

    if msg == WM_RBUTTONDOWN:
        if not (_enabled and _camera_lock and _edit_mode()):
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        # Right press unlocks the camera directly and is then passed through
        # unchanged, so ZBrush starts the rotate gesture right away.
        _right_relock_at = 0.0
        _lock_camera(False)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_RBUTTONUP:
        if not (_enabled and _camera_lock and _edit_mode()):
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        # Relock the camera 2ms after the right button is released.
        _right_relock_at = time.perf_counter() + RIGHT_RELOCK_MS / 1000.0
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_LBUTTONDOWN:
        return _begin_left(hwnd, msg, wparam, lparam)

    if msg == WM_MOUSEMOVE:
        # Swallow movement only while the probe classifies (5ms). After the
        # decision every state passes moves through.
        if _state == CLASSIFY:
            return 0
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_LBUTTONUP:
        previous = _state
        if previous == CLASSIFY:
            # The real down is still active; the real up completes the click.
            # No replay needed for quick clicks.
            user32.KillTimer(hwnd, CLASSIFY_TIMER)
            _state = IDLE
            return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        if previous in (WAIT_MODEL, START_PENDING):
            # The probe already ended the press with a synthetic UP, so ZBrush
            # is not holding a left down here; swallow the physical UP instead
            # of delivering an orphan button-up.
            _reset(hwnd)
            return 0
        _state = IDLE
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg in (WM_CANCELMODE, WM_CAPTURECHANGED):
        if not _key(VK_LBUTTON):
            _reset(hwnd)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_NCDESTROY:
        _reset(hwnd)
        user32.KillTimer(hwnd, POLL_TIMER)
        _restore_cursor_watch()
        comctl32.RemoveWindowSubclass(hwnd, _subclass, SUBCLASS_ID)
        _lock_camera(False)
        _hwnd = 0
        _installed = False
        _right_relock_at = 0.0
        _lock_state = None
        _hover_mat = None
        _hover_ready = False

    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProc
def _subclass(hwnd, msg, wparam, lparam, sid, reference):
    del sid, reference
    try:
        return _handle(hwnd, msg, wparam, lparam)
    except Exception:
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@EnumProc
def _find(hwnd, unused):
    del unused
    global _hwnd
    name = ctypes.create_unicode_buffer(64)
    if user32.GetClassNameW(hwnd, name, len(name)) and name.value == "ZBrush":
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            _hwnd = int(hwnd)
            return False
    return True


def _toggle(sender, value):
    del sender
    global _enabled, _right_relock_at, _hover_mat, _hover_ready, _lock_state
    _enabled = bool(value)
    if _hwnd:
        _reset(_hwnd)
    if not _enabled:
        _right_relock_at = 0.0
        _hover_mat = None
        _hover_ready = False
        _lock_state = None
        _lock_camera(False)
    else:
        _sync_camera()


def _toggle_cam_lock(sender, value):
    del sender
    global _camera_lock, _right_relock_at, _lock_state
    _camera_lock = bool(value)
    if _hwnd:
        _reset(_hwnd)
    if not _camera_lock:
        # Camera lock off: abort any in-flight right-button handling, unlock
        # once, then never touch the camera switch again. Right button is
        # passed through untouched; left button is still handled normally.
        _right_relock_at = 0.0
        _lock_state = None
        _lock_camera(False)
    else:
        _sync_camera()


def _open_url(url):
    try:
        os.startfile(url)
    except Exception:
        pass


def _open_bili(sender):
    del sender
    _open_url("https://space.bilibili.com/281243426?spm_id_from=333.1007.0.0")


def _open_github(sender):
    del sender
    _open_url("https://github.com/iillya/NoLeftClickRotation")


def _setup_ui():
    if zbc.exists(BODY):
        zbc.close(BODY)
    for old_palette in LEGACY_PALETTES:
        if zbc.exists(old_palette):
            zbc.close(old_palette)
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_switch(
        ENABLE_PATH, True,
        UI_TEXT["enable_info"],
        _toggle, initially_disabled=False, width=150,
    )
    zbc.add_switch(
        CAM_LOCK_PATH, True,
        UI_TEXT["camera_lock_info"],
        _toggle_cam_lock, initially_disabled=False, width=150,
    )
    zbc.add_button(
        BILI_PATH, UI_TEXT["bili_info"],
        _open_bili, initially_disabled=False, width=150,
    )
    zbc.add_button(
        GITHUB_PATH, UI_TEXT["github_info"],
        _open_github, initially_disabled=False, width=150,
    )


def main():
    global _installed
    if _installed:
        return
    try:
        _setup_ui()
        user32.EnumWindows(_find, 0)
        if not _hwnd:
            _lock_camera(False)
            return
        wid_ok = _window_id_path_works()
        if not wid_ok:
            zbc.set_notebar_text(
                "NLC V1: View Window Id unavailable; camera lock only")
        if not _install_cursor_watch():
            _lock_camera(False)
            return
        if not comctl32.SetWindowSubclass(_hwnd, _subclass, SUBCLASS_ID, 0):
            _restore_cursor_watch()
            _lock_camera(False)
            return
        if not user32.SetTimer(_hwnd, POLL_TIMER, POLL_MS, None):
            comctl32.RemoveWindowSubclass(_hwnd, _subclass, SUBCLASS_ID)
            _restore_cursor_watch()
            _lock_camera(False)
            zbc.set_notebar_text(
                "NLC V1: failed to start input polling")
            return
        _installed = True
        _sync_camera()
    except Exception as exc:
        del exc
        _lock_camera(False)


main()
