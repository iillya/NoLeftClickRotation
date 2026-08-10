# -*- coding: utf-8 -*-
"""Auto-test nav counters: idle / L-blank drag / L-mesh drag / R-drag (control)."""

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
LOG = os.path.join(os.environ["TEMP"], "nlr_navcount.log")
PLUGIN = os.path.join(
    os.environ["APPDATA"],
    r"Maxon\Maxon ZBrush 2026_F3C8B4C4\ZStartup\ZPlugs64\NoLeftClickRotation.py",
)
SRC = os.path.join(WORK, "_tools", "nlc_nav_count.py")

user32 = ctypes.WinDLL("user32")
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
user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002


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
    n = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    return n


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


def client_xy(hwnd, fx=0.5, fy=0.5):
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    return int(cr.right * fx), int(cr.bottom * fy)


def read_log():
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def wait_ready(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        cur = read_log()
        if "ready" in cur and "mat=" in cur:
            return True
        time.sleep(2)
    return False


def last_mat():
    for line in reversed(read_log().splitlines()):
        m = re.search(r"mat=(\S+)", line)
        if m:
            return m.group(1)
    return None


def probe_point(hwnd, fx, fy):
    x, y = client_pt(hwnd, fx, fy)
    user32.SetCursorPos(x, y)
    time.sleep(1.2)
    return last_mat()


def drag(hwnd, start, end, secs, button_flags):
    """PostMessage-based drag. start/end are client coords."""
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    if button_flags == "L":
        down, up, mk = WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON
    else:
        down, up, mk = WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON
    x0, y0 = start
    x1, y1 = end
    lp0 = (y0 << 16) | (x0 & 0xFFFF)
    user32.PostMessageW(hwnd, down, mk, lp0)
    time.sleep(0.5)
    steps = max(3, int(secs / 0.05))
    for i in range(1, steps + 1):
        x = x0 + (x1 - x0) * i // steps
        y = y0 + (y1 - y0) * i // steps
        lp = (y << 16) | (x & 0xFFFF)
        user32.PostMessageW(hwnd, WM_MOUSEMOVE, mk, lp)
        time.sleep(0.05)
    user32.PostMessageW(hwnd, up, 0, lp0)
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
        print("timeout, log tail:")
        print(read_log()[-2000:])
        dismiss.terminate()
        return
    print("ready, probing points...")

    # wait for the test scene document to load (mesh mat appears)
    t0 = time.time()
    while time.time() - t0 < 60:
        user32.SetCursorPos(*client_pt(hwnd, 0.5, 0.5))
        time.sleep(2)
        m = last_mat()
        if m not in (None, "0.0", "0", "?"):
            print("doc loaded, mat=%s" % m)
            break
    time.sleep(2)

    # find mesh and blank points via idle mat
    mx, my = client_xy(hwnd, 0.5, 0.5)
    bx, by = client_xy(hwnd, 0.08, 0.5)
    print("mesh client(%d,%d) blank client(%d,%d)" % (mx, my, bx, by))
    right = (bx + 160, by)

    print("idle 2s")
    time.sleep(2)
    print("L-blank drag 2s")
    drag(hwnd, (bx, by), right, 2.0, "L")
    print("idle 1s")
    time.sleep(1)
    print("L-mesh drag 2s")
    drag(hwnd, (mx - 80, my), (mx + 80, my), 2.0, "L")
    print("idle 1s")
    time.sleep(1)
    print("R-drag (control) 2s")
    drag(hwnd, (bx, by), right, 2.0, "R")
    print("idle 1s")
    time.sleep(1)
    print("L-blank drag again 2s")
    drag(hwnd, (bx, by), right, 2.0, "L")
    time.sleep(1)

    print("=== log tail ===")
    print(read_log()[-6000:])
    dismiss.terminate()


if __name__ == "__main__":
    main()
