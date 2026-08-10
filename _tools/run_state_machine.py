# -*- coding: utf-8 -*-
"""State-machine behavior test on stock ZBrush (plugin removed).
Scenario A: blank-press drag onto mesh - does rotation continue?
Scenario B: mesh-press drag off mesh - does the stroke continue?
Scenario C: slider press drag away - does the slider keep changing?
"""

import ctypes
import os
import shutil
import struct
import subprocess
import sys
import time
from ctypes import wintypes

WORK = r"C:\Users\liuwenbo\Desktop\zb插件"
ZBRUSH = r"C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
SCENE = os.path.join(os.environ["TEMP"], "test_scene.zpr")
PLUGIN = os.path.join(
    os.environ["APPDATA"],
    r"Maxon\Maxon ZBrush 2026_F3C8B4C4\ZStartup\ZPlugs64\NoLeftClickRotation.py",
)

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
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.SetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.ShowWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.PrintWindow.restype = wintypes.BOOL
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.GetWindowDC.restype = wintypes.HDC
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.restype = ctypes.c_int
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]


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


def capture(hwnd, path):
    gdi32 = ctypes.WinDLL("gdi32")
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w = r.right - r.left
    h = r.bottom - r.top
    hdc_win = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    bmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    gdi32.SelectObject(hdc_mem, bmp)
    user32.PrintWindow(hwnd, hdc_mem, 0)

    class BI(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bi = BI()
    bi.biSize = ctypes.sizeof(BI)
    bi.biWidth = w
    bi.biHeight = h
    bi.biPlanes = 1
    bi.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_win)
    with open(path, "wb") as f:
        f.write(b"BM")
        f.write(struct.pack("<IHHI", 54 + w * h * 4, 0, 0, 54))
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0, w * h * 4, 0, 0, 0, 0))
    return w, h


def diff_ratio(p1, p2, region=None):
    with open(p1, "rb") as f1, open(p2, "rb") as f2:
        d1 = f1.read()[54:]
        d2 = f2.read()[54:]
    total = 0
    diff = 0
    for i in range(0, min(len(d1), len(d2)) - 3, 4):
        total += 1
        if d1[i:i+4] != d2[i:i+4]:
            diff += 1
    return diff / max(1, total)


def drag(hwnd, start_pt, end_pt, secs, hold_extra=None):
    user32.ShowWindow(hwnd, 9)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    user32.SetCursorPos(*start_pt)
    time.sleep(0.5)
    n = send_mouse(0x0002)
    time.sleep(0.3)
    steps = max(3, int(secs / 0.1))
    for i in range(1, steps + 1):
        x = start_pt[0] + (end_pt[0] - start_pt[0]) * i // steps
        y = start_pt[1] + (end_pt[1] - start_pt[1]) * i // steps
        user32.SetCursorPos(x, y)
        time.sleep(0.1)
    if hold_extra:
        user32.SetCursorPos(*hold_extra)
        time.sleep(1.0)
    send_mouse(0x0004)
    time.sleep(0.6)


def main():
    try:
        _run()
    finally:
        if os.path.exists(PLUGIN + ".bak"):
            os.replace(PLUGIN + ".bak", PLUGIN)
        print("plugin restored")


def _run():
    # temporarily move plugin away (stock ZBrush behavior)
    if os.path.exists(PLUGIN):
        os.replace(PLUGIN, PLUGIN + ".bak")
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
    print("waiting doc load...")
    time.sleep(35)
    out = os.path.join(WORK, "_tools")

    cx, cy = client_pt(hwnd, 0.5, 0.5)
    bx, by = client_pt(hwnd, 0.08, 0.5)
    right = client_pt(hwnd, 0.8, 0.5)

    # --- Scenario A: blank press -> drag onto mesh -> keep dragging on mesh
    print("A: blank press, drag onto mesh, keep moving")
    user32.SetCursorPos(bx, by)
    time.sleep(0.5)
    send_mouse(0x0002)
    time.sleep(0.3)
    for i in range(1, 8):
        user32.SetCursorPos(bx + (cx - bx) * i // 7, by + (cy - by) * i // 7)
        time.sleep(0.1)
    # on mesh now, keep dragging right on mesh
    user32.SetCursorPos(right[0] - 30, cy)
    time.sleep(0.4)
    cap_a1 = os.path.join(out, "sm_a1.bmp")
    capture(hwnd, cap_a1)
    user32.SetCursorPos(right[0], cy)
    time.sleep(0.5)
    cap_a2 = os.path.join(out, "sm_a2.bmp")
    capture(hwnd, cap_a2)
    send_mouse(0x0004)
    time.sleep(0.6)
    print("A rotate-continue diff: %.4f" % diff_ratio(cap_a1, cap_a2))

    # --- Scenario B: mesh press -> drag off mesh -> keep moving in blank
    user32.SetCursorPos(cx, cy)
    time.sleep(0.5)
    send_mouse(0x0002)
    time.sleep(0.3)
    for i in range(1, 8):
        user32.SetCursorPos(cx + (bx - cx) * i // 7, cy + (by - cy) * i // 7)
        time.sleep(0.1)
    cap_b1 = os.path.join(out, "sm_b1.bmp")
    capture(hwnd, cap_b1)
    user32.SetCursorPos(bx, by)
    time.sleep(0.5)
    cap_b2 = os.path.join(out, "sm_b2.bmp")
    capture(hwnd, cap_b2)
    send_mouse(0x0004)
    time.sleep(0.6)
    print("B stroke-continue diff: %.4f" % diff_ratio(cap_b1, cap_b2))

    print("screenshots:", [os.path.join(out, n) for n in ("sm_a1.bmp", "sm_a2.bmp", "sm_b1.bmp", "sm_b2.bmp")])
    dismiss.terminate()


if __name__ == "__main__":
    main()
