# -*- coding: utf-8 -*-
"""Lock the ZBrush camera and unlock it through right-button events."""

import ctypes
import os
from ctypes import wintypes

from zbrush import commands as zbc


VERSION = "2.1.0"

EDIT_PATH = "Transform:Edit"
LOCK_CAMERA_PATH = "Draw:Lock Camera"

WM_CANCELMODE = 0x001F
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_NCDESTROY = 0x0082

SUBCLASS_ID = 0x52434C4B
EDIT_TIMER_REQUEST_ID = 0x52434544
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
    "palette": "Right Click Camera Unlock",
    "enable": "Enable",
    "enable_info": (
        "Lock the camera in Edit mode. Hold the right mouse button to unlock it."
    ),
    "bili": "BiliBili",
    "bili_info": "Open the author's BiliBili page",
    "github": "GitHub",
    "github_info": "Open the project on GitHub",
}

_TEXT_ZH = {
    "palette": "右键解锁相机",
    "enable": "启用",
    "enable_info": "在 Edit 模式下锁定相机；按住右键时临时解锁。",
    "bili": "哔哩哔哩",
    "bili_info": "打开作者的哔哩哔哩主页",
    "github": "GitHub",
    "github_info": "打开项目的 GitHub 页面",
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
TimerProc = ctypes.WINFUNCTYPE(
    None,
    wintypes.HWND,
    wintypes.UINT,
    ctypes.c_size_t,
    wintypes.DWORD,
)

user32 = ctypes.WinDLL("user32", use_last_error=True)
comctl32 = ctypes.WinDLL("comctl32", use_last_error=True)

user32.EnumWindows.argtypes = [EnumProc, wintypes.LPARAM]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
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
_edit_mode = False
_camera_state = None
_edit_timer_id = 0
_timer_callback = None


def _get_switch(path, default=False):
    try:
        return bool(zbc.exists(path) and float(zbc.get(path)))
    except Exception:
        return default


def _set_switch(path, value):
    value = bool(value)
    try:
        if _get_switch(path) == value:
            return True
        try:
            zbc.set(path, float(value))
        except Exception:
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


def _refresh_edit_mode():
    global _edit_mode
    current = _get_switch(EDIT_PATH)
    if current == _edit_mode:
        return
    _edit_mode = current
    _set_camera(_enabled and _edit_mode and not _right_down)


def _handle_right_down(hwnd, msg, wparam, lparam):
    global _right_down
    _right_down = True
    if _enabled and _edit_mode:
        # Unlock before ZBrush receives the press, so rotation starts at once.
        _set_camera(False)
    return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


def _handle_right_up(hwnd, msg, wparam, lparam):
    global _right_down
    # Let ZBrush finish its native right-button gesture before relocking.
    result = comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    _right_down = False
    if _enabled and _edit_mode:
        _set_camera(True)
    return result


@SubclassProc
def _subclass(hwnd, msg, wparam, lparam, subclass_id, reference):
    del subclass_id, reference
    global _camera_state, _hook_installed, _hwnd, _right_down

    try:
        if msg == WM_RBUTTONDOWN:
            return _handle_right_down(hwnd, msg, wparam, lparam)

        if msg == WM_RBUTTONUP:
            return _handle_right_up(hwnd, msg, wparam, lparam)

        if msg == WM_CANCELMODE:
            _right_down = False
            if _enabled and _edit_mode:
                _set_camera(True)

        if msg == WM_NCDESTROY:
            comctl32.RemoveWindowSubclass(hwnd, _subclass, SUBCLASS_ID)
            _hook_installed = False
            _hwnd = 0
            _right_down = False
            _camera_state = None

        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)
    except Exception:
        # Never consume a native ZBrush message when plugin handling fails.
        return comctl32.DefSubclassProc(hwnd, msg, wparam, lparam)


@EnumProc
def _find_zbrush_window(hwnd, unused):
    del unused
    global _hwnd

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


def _install_right_button_hook():
    global _hook_installed
    if _hook_installed:
        return True

    user32.EnumWindows(_find_zbrush_window, 0)
    if not _hwnd:
        return False

    if not comctl32.SetWindowSubclass(_hwnd, _subclass, SUBCLASS_ID, 0):
        return False

    _hook_installed = True
    return True


def _remove_right_button_hook():
    global _hook_installed
    if not (_hook_installed and _hwnd):
        return
    comctl32.RemoveWindowSubclass(_hwnd, _subclass, SUBCLASS_ID)
    _hook_installed = False


@TimerProc
def _on_edit_timer(hwnd, message, timer_id, tick):
    del hwnd, message, tick
    if int(timer_id) != _edit_timer_id:
        return
    try:
        _refresh_edit_mode()
    except Exception:
        pass


def _start_edit_timer():
    global _edit_timer_id, _timer_callback
    if _edit_timer_id:
        return True

    _timer_callback = _on_edit_timer
    timer_id = user32.SetTimer(
        None,
        EDIT_TIMER_REQUEST_ID,
        EDIT_POLL_MS,
        ctypes.cast(_timer_callback, ctypes.c_void_p),
    )
    if not timer_id:
        _timer_callback = None
        return False

    _edit_timer_id = int(timer_id)
    return True


def _disable_unavailable():
    global _enabled, _camera_state
    _enabled = False
    _camera_state = None
    _set_switch(LOCK_CAMERA_PATH, False)
    try:
        zbc.set_status(ENABLE_PATH, False)
        zbc.set_notebar_text("右键解锁相机插件不可用")
    except Exception:
        pass


def _toggle(sender, value):
    del sender
    global _enabled, _camera_state
    _enabled = bool(value)
    _camera_state = None
    _refresh_edit_mode()
    _set_camera(_enabled and _edit_mode and not _right_down)


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
    global _edit_mode, _initialized
    if _initialized:
        return

    _initialized = True
    _setup_ui()
    _edit_mode = _get_switch(EDIT_PATH)

    if not _install_right_button_hook():
        _disable_unavailable()
        return

    if not _start_edit_timer():
        _remove_right_button_hook()
        _disable_unavailable()
        return

    _set_camera(_enabled and _edit_mode)


main()
