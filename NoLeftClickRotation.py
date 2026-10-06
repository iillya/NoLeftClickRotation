# -*- coding: utf-8 -*-
"""Lock the ZBrush camera and unlock it through right-button events."""

import ctypes
import os
from ctypes import wintypes

from zbrush import commands as zbc


# Reload must detach the previous native callback before replacing its globals.
# Keep the old callback alive until the new instance has been constructed.
_previous_runtime = getattr(zbc, "_no_left_click_rotation_runtime", None)
if _previous_runtime is not None and not _previous_runtime["shutdown"]():
    raise RuntimeError("Could not detach the previous NoLeftClickRotation instance")


VERSION = "2.1.0"

EDIT_PATH = "Transform:Edit"
LOCK_CAMERA_PATH = "Draw:Lock Camera"

WM_CANCELMODE = 0x001F
WM_ACTIVATEAPP = 0x001C
WM_MOUSEMOVE = 0x0200
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_RBUTTONDBLCLK = 0x0206
WM_CAPTURECHANGED = 0x0215
WM_NCDESTROY = 0x0082
WM_TIMER = 0x0113
MK_RBUTTON = 0x0002
VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
SM_SWAPBUTTON = 23

SUBCLASS_ID = 0x52434C4B
EDIT_POLL_MS = 100

BILI_URL = "https://space.bilibili.com/281243426?spm_id_from=333.1007.0.0"
GITHUB_URL = "https://github.com/iillya/NoLeftClickRotation"


def _system_language_is_chinese():
    try:
        get_language = ctypes.windll.kernel32.GetUserDefaultUILanguage
        get_language.restype = wintypes.WORD
        return (int(get_language()) & 0x03FF) == 0x0004
    except Exception:
        return False


_TEXT_EN = {
    "palette": "No Left Click Rotation",
    "enable": "Enable",
    "enable_info": (
        "Lock the camera in Edit mode. Hold the right mouse button to unlock it."
    ),
    "bili": "BiliBili",
    "bili_info": "Open the author's BiliBili page",
    "github": "GitHub",
    "github_info": "Open the project on GitHub",
    "unavailable": "No Left Click Rotation is unavailable",
}

_TEXT_ZH = {
    "palette": "禁用左键导航",
    "enable": "启用",
    "enable_info": "在 Edit 模式下锁定相机；按住右键时临时解锁。",
    "bili": "哔哩哔哩",
    "bili_info": "打开作者的哔哩哔哩主页",
    "github": "GitHub",
    "github_info": "打开项目的 GitHub 页面",
    "unavailable": "禁用左键导航插件不可用",
}

UI_TEXT = _TEXT_ZH if _system_language_is_chinese() else _TEXT_EN

PALETTE = "Zplugin:" + UI_TEXT["palette"]
ENABLE_PATH = PALETTE + ":" + UI_TEXT["enable"]
BILI_PATH = PALETTE + ":" + UI_TEXT["bili"]
GITHUB_PATH = PALETTE + ":" + UI_TEXT["github"]

LEGACY_PALETTES = (
    "Zplugin:No Left Click Rotation",
    "Zplugin:禁用左键导航",
    "Zplugin:Right Click Camera Unlock",
    "Zplugin:右键解锁相机",
)
LEGACY_BODY = "Zplugin:No Left Click Rotation:V1"

LRESULT = ctypes.c_ssize_t
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t

SubclassProc = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
    ctypes.c_size_t,
    ctypes.c_size_t,
)
EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [EnumProc, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.SetTimer.restype = ctypes.c_size_t
user32.SetTimer.argtypes = [
    wintypes.HWND,
    ctypes.c_size_t,
    wintypes.UINT,
    ctypes.c_void_p,
]
user32.KillTimer.restype = wintypes.BOOL
user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetCurrentThreadId.argtypes = []

comctl32.SetWindowSubclass.restype = wintypes.BOOL
comctl32.SetWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProc,
    ctypes.c_size_t,
    ctypes.c_size_t,
]
comctl32.DefSubclassProc.restype = LRESULT
comctl32.DefSubclassProc.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    WPARAM,
    LPARAM,
]
comctl32.RemoveWindowSubclass.argtypes = [
    wintypes.HWND,
    SubclassProc,
    ctypes.c_size_t,
]
comctl32.RemoveWindowSubclass.restype = wintypes.BOOL

_enabled = True
_initialized = False
_hwnd = 0
_hook_installed = False
_right_down = False
_capture_lost = False
_edit_mode = False
_camera_state = None
_edit_timer_id = 0
_dispatch_depth = 0


def _get_switch(path):
    """Return None on missing/unreadable controls, distinct from an off switch."""
    try:
        if zbc.exists(path):
            return bool(float(zbc.get(path)))
    except Exception:
        pass
    return None


def _set_switch(path, value):
    value = bool(value)
    try:
        current = _get_switch(path)
        if current is None:
            return False
        if current == value:
            return True
        try:
            zbc.set(path, float(value))
        except Exception:
            # A setter can change the control and then raise. Never blindly
            # toggle it a second time, or treat a failed read as "off".
            current = _get_switch(path)
            if current is None:
                return False
            if current == value:
                return True
            zbc.toggle(path)
        return _get_switch(path) == value
    except Exception:
        return False


def _set_camera(value):
    global _camera_state
    value = bool(value)
    if value == _camera_state:
        return
    if _set_switch(LOCK_CAMERA_PATH, value):
        _camera_state = value
    else:
        _camera_state = None


def _refresh_edit_mode():
    global _edit_mode, _camera_state
    current = _get_switch(EDIT_PATH)
    if current is None:
        return
    changed = current != _edit_mode
    _edit_mode = current
    if changed:
        _camera_state = None
    if changed or _camera_state is None:
        _set_camera(_enabled and _edit_mode and not _right_down)


def _handle_right_down():
    global _right_down, _camera_state, _capture_lost
    _right_down = True
    _capture_lost = False
    if _enabled:
        # Re-read Edit at the event boundary instead of relying on the last
        # 100 ms tick; force verification if the host changed Lock Camera.
        _camera_state = None
        _refresh_edit_mode()


def _handle_right_up():
    global _right_down, _camera_state, _capture_lost
    _right_down = False
    _capture_lost = False
    if _enabled:
        _camera_state = None
        _refresh_edit_mode()


def _cancel_right_gesture():
    global _right_down, _camera_state, _capture_lost
    _right_down = False
    _capture_lost = False
    # Defer ZBrush API calls until the timer. Capture/focus messages can be
    # nested inside ZBrush's native mouse handler or modal-dialog setup.
    if _enabled:
        _camera_state = None


def _on_edit_timer():
    if not _enabled or _dispatch_depth != 1:
        return
    if _capture_lost:
        # GetAsyncKeyState reads physical buttons; mouse messages are logical.
        key = VK_LBUTTON if user32.GetSystemMetrics(SM_SWAPBUTTON) else VK_RBUTTON
        if not (user32.GetAsyncKeyState(key) & 0x8000):
            _cancel_right_gesture()
    _refresh_edit_mode()


@SubclassProc
def _subclass(hwnd, msg, wparam, lparam, subclass_id, reference):
    del subclass_id, reference
    global _camera_state, _hook_installed, _hwnd, _right_down
    global _enabled, _initialized, _dispatch_depth, _edit_timer_id, _capture_lost

    _dispatch_depth += 1
    try:
        if msg == WM_TIMER and _edit_timer_id and wparam == _edit_timer_id:
            try:
                _on_edit_timer()
            except Exception:
                pass
            return 0  # Consume only our timer, including when its work fails.
        try:
            if msg in (WM_RBUTTONDOWN, WM_RBUTTONDBLCLK):
                _handle_right_down()
            elif msg == WM_CANCELMODE or (msg == WM_ACTIVATEAPP and not wparam):
                _cancel_right_gesture()
            elif msg == WM_CAPTURECHANGED and _right_down:
                # Capture may move to a child while the gesture is still held.
                _capture_lost = True
            elif msg == WM_MOUSEMOVE and _right_down and not (wparam & MK_RBUTTON):
                _cancel_right_gesture()
            elif msg == WM_NCDESTROY:
                _enabled = False
                _initialized = False
                try:
                    _stop_edit_timer()
                finally:
                    try:
                        _remove_right_button_hook()
                    finally:
                        # Windows releases window-owned resources on destroy,
                        # even if explicit removal already reports failure.
                        _edit_timer_id = 0
                        _hook_installed = False
                        _hwnd = 0
                        _right_down = False
                        _capture_lost = False
                        _camera_state = None
        except Exception:
            # Plugin failure must not suppress or repeat a native input event.
            pass

        # Exactly one forwarding site. Post-processing errors must not call
        # DefSubclassProc again after the host already handled the event.
        try:
            result = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
        except Exception:
            # Never retry a native call or let a Python exception escape the
            # ctypes callback with an undefined return value.
            return 0
        if msg == WM_RBUTTONUP and _hook_installed and _hwnd == hwnd:
            try:
                _handle_right_up()
            except Exception:
                pass
        return result
    finally:
        _dispatch_depth -= 1


@EnumProc
def _find_zbrush_window(hwnd, unused):
    del unused
    global _hwnd

    try:
        class_name = ctypes.create_unicode_buffer(64)
        if not user32.GetClassNameW(hwnd, class_name, len(class_name)):
            return True
        if class_name.value != "ZBrush":
            return True

        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        if process_id.value != os.getpid():
            return True

        _hwnd = int(hwnd)
        return False
    except Exception:
        return True


def _install_right_button_hook():
    global _hook_installed, _hwnd
    if _hook_installed:
        return True

    _hwnd = 0
    user32.EnumWindows(_find_zbrush_window, 0)
    if not _hwnd:
        return False
    if user32.GetWindowThreadProcessId(_hwnd, None) != kernel32.GetCurrentThreadId():
        return False  # SetWindowSubclass must run on the window's owning thread.

    if not comctl32.SetWindowSubclass(_hwnd, _subclass, SUBCLASS_ID, 0):
        return False

    _hook_installed = True
    return True


def _remove_right_button_hook():
    global _hook_installed
    if not (_hook_installed and _hwnd):
        return True
    if not comctl32.RemoveWindowSubclass(_hwnd, _subclass, SUBCLASS_ID):
        return False
    _hook_installed = False
    return True


def _start_edit_timer():
    global _edit_timer_id
    if _edit_timer_id:
        return True

    if not (_hook_installed and _hwnd):
        return False
    # Window timers use the requested ID, not the SetTimer return value.
    # No TIMERPROC pointer can outlive the plugin through queued WM_TIMERs.
    request_id = id(_subclass)
    if not user32.SetTimer(_hwnd, request_id, EDIT_POLL_MS, None):
        return False
    _edit_timer_id = request_id
    return True


def _stop_edit_timer():
    global _edit_timer_id
    if not _edit_timer_id:
        return True
    if not user32.KillTimer(_hwnd, _edit_timer_id):
        return False
    _edit_timer_id = 0
    return True


def _shutdown():
    """Detach before a script reload; retain callbacks if removal fails."""
    global _enabled, _initialized, _right_down, _camera_state, _hwnd
    global _capture_lost
    if _dispatch_depth:
        return False
    if _hwnd and user32.GetWindowThreadProcessId(_hwnd, None) != kernel32.GetCurrentThreadId():
        return False
    _enabled = False
    _right_down = False
    _capture_lost = False
    _camera_state = None
    timer_stopped = _stop_edit_timer()
    hook_removed = _remove_right_button_hook() if timer_stopped else False
    if _hwnd:
        _set_camera(False)
    if not (timer_stopped and hook_removed):
        return False
    _hwnd = 0
    _initialized = False
    return True


def _disable_unavailable():
    global _enabled, _camera_state
    _enabled = False
    _camera_state = None
    _stop_edit_timer()
    _set_switch(LOCK_CAMERA_PATH, False)
    try:
        _set_switch(ENABLE_PATH, False)
        zbc.set_status(ENABLE_PATH, False)
        zbc.set_notebar_text(UI_TEXT["unavailable"])
    except Exception:
        pass


def _toggle(sender, value):
    del sender
    global _enabled, _camera_state
    _enabled = bool(value)
    _camera_state = None
    if not _enabled:
        _stop_edit_timer()
        _set_camera(False)
    elif _start_edit_timer():
        _refresh_edit_mode()
    else:
        _disable_unavailable()


def _open_url(url):
    try:
        os.startfile(url)
    except Exception:
        pass


def _open_bili(sender):
    del sender
    _open_url(BILI_URL)


def _open_github(sender):
    del sender
    _open_url(GITHUB_URL)


def _setup_ui():
    if zbc.exists(LEGACY_BODY):
        zbc.close(LEGACY_BODY)

    for old_palette in LEGACY_PALETTES:
        if old_palette != PALETTE and zbc.exists(old_palette):
            zbc.close(old_palette)

    if zbc.exists(PALETTE):
        zbc.close(PALETTE)

    zbc.add_subpalette(PALETTE, title_mode=0)
    zbc.add_switch(
        ENABLE_PATH,
        True,
        UI_TEXT["enable_info"],
        _toggle,
        initially_disabled=False,
        width=1,
        height=0.125,
    )
    zbc.add_button(
        BILI_PATH,
        UI_TEXT["bili_info"],
        _open_bili,
        initially_disabled=False,
        width=0.5,
        height=0.125,
    )
    zbc.add_button(
        GITHUB_PATH,
        UI_TEXT["github_info"],
        _open_github,
        initially_disabled=False,
        width=0.5,
        height=0.125,
    )


def main():
    global _initialized
    if _initialized:
        return

    _setup_ui()

    if not _install_right_button_hook():
        _disable_unavailable()
        return

    if not _start_edit_timer():
        _remove_right_button_hook()
        _disable_unavailable()
        return

    _initialized = True
    _refresh_edit_mode()


zbc._no_left_click_rotation_runtime = {"shutdown": _shutdown, "callback": _subclass}
_previous_runtime = None
main()
