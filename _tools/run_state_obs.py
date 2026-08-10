# -*- coding: utf-8 -*-
"""Drive ZBrush with reliable input and observe nav/sculpt hooks."""

import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

WORK = r"C:\Users\liuwenbo\Desktop\zb插件"
ZBRUSH = r"C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
SCENE = os.path.join(os.environ["TEMP"], "test_scene.zpr")
LOG = os.path.join(os.environ["TEMP"], "nlr_state.log")
PLUGIN = os.path.join(
    os.environ["APPDATA"],
    r"Maxon\Maxon ZBrush 2026_F3C8B4C4\ZStartup\ZPlugs64\NoLeftClickRotation.py",
)
SRC = os.path.join(WORK, "_tools", "nlc_state_obs.py")

user32 = ctypes.WinDLL("user32")
kernel32 = ctypes.WinDLL("kernel32")
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClientRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.AttachThreadInput.restype = wintypes.BOOL
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetCurrentThreadId.restype = wintypes.DWORD


class INPUT(ctypes.Structure):
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]
    _anonymous_ = ("mi",)
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]


user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


def send_mouse(flags):
    inp = INPUT()
    inp.type = 0
    inp.mi.dwFlags = flags
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def foreground(hwnd):
    user32.ShowWindow(hwnd, 9)
    tid_zb = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(tid_zb))
    tid_me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(tid_me, tid_zb.value, True)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(tid_me, tid_zb.value, False)
    time.sleep(0.5)


def find_zb():
    found = [None]

    @WNDENUMPROC
    def cb(hwnd, lp):
        buf = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, buf, 64)
        if buf.value == "ZBrush":
            found[0] = hwnd
            return False
        return True

    user32.EnumWindows(cb, 0)
    return found[0]


def client_pt(hwnd, fx=0.5, fy=0.5):
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    tl = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    return tl.x + int(cr.right * fx), tl.y + int(cr.bottom * fy)


def read_log():
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def wait_ready(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if "ready" in read_log():
            return True
        time.sleep(2)
    return False


def press_hold(hwnd, pt, btn_down, btn_up, secs):
    foreground(hwnd)
    user32.SetCursorPos(*pt)
    time.sleep(0.5)
    send_mouse(btn_down)
    time.sleep(0.3)
    # verify via log down flag for left
    time.sleep(secs)
    send_mouse(btn_up)
    time.sleep(0.6)


def main():
    shutil.copyfile(SRC, PLUGIN)
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process -Name ZBrush -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True,
    )
    time.sleep(3)
    dismiss = subprocess.Popen(
        [sys.executable, os.path.join(WORK, "_tools", "dismiss_dialog.py")],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    subprocess.Popen([ZBRUSH, SCENE])
    hwnd = None
    for _ in range(60):
        time.sleep(2)
        hwnd = find_zb()
        if hwnd:
            break
    if not hwnd:
        print("no window")
        dismiss.terminate()
        return
    print("waiting ready...")
    if not wait_ready():
        print("timeout")
        dismiss.terminate()
        return
    print("ready, waiting doc...")
    time.sleep(30)

    bx, by = client_pt(hwnd, 0.08, 0.5)
    mx, my = client_pt(hwnd, 0.5, 0.5)
    print("idle 2s")
    time.sleep(2)
    print("blank press 2.5s")
    press_hold(hwnd, (bx, by), 0x0002, 0x0004, 2.5)
    print("idle 1s")
    time.sleep(1)
    print("mesh press 2.5s")
    press_hold(hwnd, (mx, my), 0x0002, 0x0004, 2.5)
    print("idle 1s")
    time.sleep(1)
    print("right press 2.5s")
    press_hold(hwnd, (bx, by), 0x0008, 0x0010, 2.5)
    time.sleep(1)

    print("=== log tail ===")
    print(read_log()[-8000:])
    dismiss.terminate()


if __name__ == "__main__":
    main()
