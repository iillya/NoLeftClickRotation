# -*- coding: utf-8 -*-
"""Bridge a blank-canvas left drag into sculpting when it reaches a model.

ZBrush 2026.1.1 / Windows only. UI and mesh input pass through unchanged. A
blank-canvas down is held until its drag reaches a model. The plug-in is
deliberately inactive outside Edit mode.
"""

import ctypes
import os
import struct
import time
from ctypes import wintypes


PLUGIN_VERSION = "Candidate 1"

# Win32 messages and key flags.
WM_TIMER = 0x0113
WM_CANCELMODE = 0x001F
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200
WM_CAPTURECHANGED = 0x0215
WM_NCDESTROY = 0x0082

MK_LBUTTON = 0x0001
MK_SHIFT = 0x0004
MK_CONTROL = 0x0008
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12

CANVAS_WINDOW_ID = 1004
POLL_INTERVAL_MS = 10
RIGHT_RELEASE_LOCK_DELAY_SECONDS = 0.010
TIMER_ID = 0x4E4C5231
SUBCLASS_ID = 0x4E4C5231

# Gesture states.
IDLE = 0
UI_PASS = 1
MESH_PASS = 2
WAIT_FOR_MESH = 3
BRIDGED = 4

# ZBrush paths.
WINDOW_ID_PATH = "Preferences:Utilities:View Window Id"
EDIT_PATH = "Transform:Edit"
LOCK_CAMERA_PATH = "Draw:Lock Camera"
LIGHTBOX_BUTTON_PATH = "Preferences:LightBox:LightBox"

# Reverse-engineered for ZBrush.exe 2026.1.1.1.
# The instruction loads the global state pointer used by the native PixolPick
# canvas-selection branch. Its RIP displacement is decoded at runtime.
PIXOL_STATE_LOAD_RVA = 0x5EDAC2
PIXOL_STATE_LOAD_SIGNATURE = bytes.fromhex("488b0587ebc91b")
PIXOL_FLAGS_OFFSET = 0x11584
PIXOL_STABLE_CANVAS_BIT = 0x00200000

PLUGIN_NAME = "No Left Click Rotation"
PALETTE = "Zplugin:" + PLUGIN_NAME
BODY = PALETTE + ":Body"
SWITCH_PATH = BODY + ":Enable"

LOG_PATH = os.path.join(
    os.environ.get("TEMP", os.path.dirname(__file__)),
    "NoLeftClickRotation.log",
)

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
UINT_PTR = ctypes.c_size_t

user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

SubclassProc = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
    ctypes.c_void_p,
    ctypes.c_void_p,
)
EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
)

kernel32.GetModuleHandleW.restype = ctypes.c_void_p
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetCursorPos.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.SetTimer.restype = UINT_PTR
user32.SetTimer.argtypes = [
    wintypes.HWND,
    UINT_PTR,
    wintypes.UINT,
    ctypes.c_void_p,
]
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, UINT_PTR]
user32.SendMessageW.restype = LRESULT
user32.SendMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]
comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProc,
    UINT_PTR,
    UINT_PTR,
]
comctl32.RemoveWindowSubclass.restype = wintypes.BOOL
comctl32.RemoveWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProc,
    UINT_PTR,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]

_enabled = True
_hwnd = 0
_gesture = IDLE
_injecting = False
_pixol_flags_address = 0
_version_ok = False
_last_status = ""
_camera_session = False
_right_was_down = False
_right_unlock_until = 0.0
_lightbox_overlay_open = False


def _log(message):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as stream:
            stream.write("%s %s\n" % (time.strftime("%H:%M:%S"), message))
    except OSError:
        pass


def _key_down(vkey):
    return bool(user32.GetAsyncKeyState(vkey) & 0x8000)


def _zbrush_switch(path, default=False):
    try:
        import zbrush.commands as zbc

        if not zbc.exists(path):
            return default
        return bool(float(zbc.get(path)))
    except Exception:
        return default


def _active():
    return _enabled and _version_ok and _zbrush_switch(EDIT_PATH, False)


def _lightbox_flags():
    try:
        import zbrush.commands as zbc

        return int(zbc.get_flags(LIGHTBOX_BUTTON_PATH))
    except Exception:
        return -1


def _lightbox_open():
    return _lightbox_overlay_open


def _is_canvas():
    return _window_id() == CANVAS_WINDOW_ID


def _window_id():
    try:
        import zbrush.commands as zbc

        return int(round(float(zbc.get(WINDOW_ID_PATH))))
    except Exception:
        return -1


def _material_under_pointer():
    """Read mat from the stable canvas buffer, restoring all native state."""

    if not _pixol_flags_address:
        return 0.0
    import zbrush.commands as zbc

    x, y = zbc.get_mouse_pos(global_coordinates=False)
    flags = ctypes.c_uint32.from_address(_pixol_flags_address)
    original = flags.value
    try:
        flags.value = original | PIXOL_STABLE_CANVAS_BIT
        return float(zbc.pixol_pick(5, float(x), float(y)))
    finally:
        flags.value = original


def _pointer_on_mesh():
    try:
        return _material_under_pointer() != 0.0
    except Exception as exception:
        _log("pixol_error=" + repr(exception))
        return False


def _set_zbrush_switch(path, value):
    try:
        import zbrush.commands as zbc

        current = _zbrush_switch(path, bool(value))
        if current == bool(value):
            return True
        try:
            zbc.set(path, 1.0 if value else 0.0)
        except Exception:
            zbc.toggle(path)
        return _zbrush_switch(path, not bool(value)) == bool(value)
    except Exception:
        return False


def _sync_camera_lock():
    global _camera_session, _right_was_down, _right_unlock_until

    controlled = _active()
    if not controlled:
        if _camera_session or not _enabled:
            _set_zbrush_switch(LOCK_CAMERA_PATH, False)
        _camera_session = False
        _right_was_down = False
        _right_unlock_until = 0.0
        return

    if not _camera_session:
        _camera_session = True

    now = time.perf_counter()
    right_down = _key_down(VK_RBUTTON)
    if right_down:
        _right_was_down = True
        _right_unlock_until = 0.0
        _set_zbrush_switch(LOCK_CAMERA_PATH, False)
        return

    if _right_was_down:
        _right_was_down = False
        _right_unlock_until = now + RIGHT_RELEASE_LOCK_DELAY_SECONDS

    if now < _right_unlock_until:
        _set_zbrush_switch(LOCK_CAMERA_PATH, False)
        return

    _right_unlock_until = 0.0
    _set_zbrush_switch(LOCK_CAMERA_PATH, True)


def _reset_gesture():
    global _gesture
    _gesture = IDLE


def _mouse_lparam(hwnd):
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        return 0
    if not user32.ScreenToClient(hwnd, ctypes.byref(point)):
        return 0
    return ((point.y & 0xFFFF) << 16) | (point.x & 0xFFFF)


def _mouse_wparam():
    return _modifier_wparam() | MK_LBUTTON


def _modifier_wparam():
    value = 0
    if _key_down(VK_SHIFT):
        value |= MK_SHIFT
    if _key_down(VK_CONTROL):
        value |= MK_CONTROL
    return value


def _start_sculpting(hwnd):
    """Deliver the gesture's first native down at the current model point."""

    global _gesture, _injecting
    _gesture = BRIDGED
    _injecting = True
    try:
        wparam = _mouse_wparam()
        lparam = _mouse_lparam(hwnd)
        user32.SendMessageW(hwnd, WM_LBUTTONDOWN, wparam, lparam)
        user32.SendMessageW(hwnd, WM_MOUSEMOVE, wparam, lparam)
        _status("MODEL FOUND: sculpting started")
    finally:
        _injecting = False


def _status(message):
    global _last_status
    if message == _last_status:
        return
    _last_status = message
    _log(message)
    try:
        import zbrush.commands as zbc

        zbc.set_notebar_text("NLR: " + message)
    except Exception:
        pass


def _begin_left(hwnd, msg, wparam, lparam):
    global _gesture, _lightbox_overlay_open

    flags = _lightbox_flags()
    window_id = _window_id()
    # 0x8 is present both on the normal canvas and inside LightBox, so it is
    # not a visibility bit. 0x4 appears only while the LightBox switch is
    # being pressed. Use that edge without depending on a View Window ID.
    if flags >= 0 and flags & 0x4:
        _lightbox_overlay_open = not _lightbox_overlay_open
        _gesture = UI_PASS
        _log(
            "LB flags=%#x wid=%d decision=PASS_LIGHTBOX_TOGGLE open=%d"
            % (flags, window_id, int(_lightbox_overlay_open))
        )
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if not _active():
        _reset_gesture()
        _log("LB flags=%#x wid=%d decision=PASS_INACTIVE" % (flags, window_id))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if _lightbox_open():
        _gesture = UI_PASS
        _log("LB flags=%#x wid=%d decision=PASS_LIGHTBOX" % (flags, window_id))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if window_id != CANVAS_WINDOW_ID:
        _gesture = UI_PASS
        _log("LB flags=%#x wid=%d decision=PASS_UI" % (flags, window_id))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if _pointer_on_mesh():
        _gesture = MESH_PASS
        _log("LB flags=%#x wid=%d decision=PASS_MESH" % (flags, window_id))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    # Preserve native Ctrl/Alt canvas gestures (masking/navigation shortcuts).
    if _key_down(VK_CONTROL) or _key_down(VK_MENU):
        _gesture = UI_PASS
        _log("LB flags=%#x wid=%d decision=PASS_MODIFIER" % (flags, window_id))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    _gesture = WAIT_FOR_MESH
    _log("LB flags=%#x wid=%d decision=SWALLOW_BLANK" % (flags, window_id))
    _status("blank canvas: waiting for model")
    return 0


def _poll_waiting(hwnd):
    if _gesture != WAIT_FOR_MESH:
        return
    if not _active() or _lightbox_open() or not _key_down(VK_LBUTTON):
        _reset_gesture()
        return
    if _pointer_on_mesh():
        _start_sculpting(hwnd)


def _handle(hwnd, msg, wparam, lparam):
    global _gesture

    if _injecting:
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_TIMER and int(wparam) == TIMER_ID:
        _sync_camera_lock()
        _poll_waiting(hwnd)
        return 0

    if msg == WM_LBUTTONDOWN:
        return _begin_left(hwnd, msg, wparam, lparam)

    if msg == WM_MOUSEMOVE:
        if _gesture == WAIT_FOR_MESH:
            _poll_waiting(hwnd)
            if _gesture == WAIT_FOR_MESH:
                return 0
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_LBUTTONUP:
        previous = _gesture
        _reset_gesture()
        if previous == WAIT_FOR_MESH:
            _status("blank gesture discarded")
            return 0
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg in (WM_CANCELMODE, WM_CAPTURECHANGED):
        _reset_gesture()
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    if msg == WM_NCDESTROY:
        global _camera_session
        if _camera_session:
            _set_zbrush_switch(LOCK_CAMERA_PATH, False)
            _camera_session = False
        user32.KillTimer(hwnd, TIMER_ID)
        comctl32.RemoveWindowSubclass(hwnd, _subclass, SUBCLASS_ID)
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)

    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@SubclassProc
def _subclass(hwnd, msg, wparam, lparam, subclass_id, reference_data):
    del subclass_id, reference_data
    try:
        return _handle(hwnd, msg, wparam, lparam)
    except Exception as exception:
        _log("callback_error=" + repr(exception))
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@EnumWindowsProc
def _find_zbrush(hwnd, lparam):
    del lparam
    global _hwnd
    try:
        class_name = ctypes.create_unicode_buffer(128)
        if user32.GetClassNameW(hwnd, class_name, len(class_name)):
            if class_name.value == "ZBrush":
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == os.getpid():
                    _hwnd = int(hwnd)
                    return False
    except Exception:
        pass
    return True


def _validate_native_layout():
    """Resolve the private flag only when the exact instruction matches."""

    global _pixol_flags_address, _version_ok
    image_base = int(kernel32.GetModuleHandleW(None) or 0)
    site = image_base + PIXOL_STATE_LOAD_RVA
    actual = ctypes.string_at(site, len(PIXOL_STATE_LOAD_SIGNATURE))
    if actual != PIXOL_STATE_LOAD_SIGNATURE:
        _log("unsupported_signature=" + actual.hex())
        return False

    displacement = struct.unpack("<i", actual[3:7])[0]
    pointer_slot = site + 7 + displacement
    state = ctypes.c_void_p.from_address(pointer_slot).value
    if not state:
        _log("state_pointer_is_null")
        return False

    _pixol_flags_address = int(state) + PIXOL_FLAGS_OFFSET
    # A readable round-trip is sufficient; the value itself is dynamic.
    ctypes.c_uint32.from_address(_pixol_flags_address).value
    _version_ok = True
    _log(
        "native_layout_ok image=%#x slot=%#x flags=%#x"
        % (image_base, pointer_slot, _pixol_flags_address)
    )
    return True


def _toggle(sender, value):
    del sender
    global _enabled
    _enabled = bool(value)
    _reset_gesture()
    _sync_camera_lock()
    _status("enabled" if _enabled else "disabled")


def _setup_ui():
    import zbrush.commands as zbc

    if zbc.exists(PALETTE):
        zbc.close(PALETTE)
    if zbc.exists(BODY):
        zbc.close(BODY)
    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_subpalette(BODY, title_mode=2)
    zbc.add_switch(
        SWITCH_PATH,
        True,
        "Edit mode only. UI and model input pass through; blank drags start sculpting when they reach a model.",
        _toggle,
        initially_disabled=False,
        width=1.0,
    )


def main():
    with open(LOG_PATH, "w", encoding="utf-8") as stream:
        stream.write(
            "=== NoLeftClickRotation 2026.1.1 - %s ===\n" % PLUGIN_VERSION
        )

    try:
        _setup_ui()
    except Exception as exception:
        _log("ui_error=" + repr(exception))

    if not _validate_native_layout():
        _status("unsupported ZBrush version; disabled")
        return

    user32.EnumWindows(_find_zbrush, 0)
    if not _hwnd:
        _log("ZBrush_window_not_found")
        return
    if not comctl32.SetWindowSubclass(_hwnd, _subclass, SUBCLASS_ID, 0):
        _log("SetWindowSubclass_failed")
        return
    if not user32.SetTimer(_hwnd, TIMER_ID, POLL_INTERVAL_MS, None):
        comctl32.RemoveWindowSubclass(_hwnd, _subclass, SUBCLASS_ID)
        _log("SetTimer_failed")
        return
    _sync_camera_lock()
    _status("ready")


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        _log("fatal=" + repr(exception))
