# -*- coding: utf-8 -*-
"""Acceptance test for the final plugin: bridge, mesh stroke, ctrl mask, rmb rotate."""

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
SRC = os.path.join(WORK, "NoLeftClickRotation.py")

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
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


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
        f.write(buf.raw)
    return w, h


def diff_ratio(p1, p2):
    with open(p1, "rb") as f1, open(p2, "rb") as f2:
        d1 = f1.read()[54:]
        d2 = f2.read()[54:]
    n = min(len(d1), len(d2))
    diff = 0
    for i in range(0, n - 3, 4):
        if d1[i:i+4] != d2[i:i+4]:
            diff += 1
    return diff / max(1, n // 4)


def stroke_pass(hwnd, cx, cy, passes=5, dx=0.25, wait=0.25):
    for i in range(passes):
        x = cx + (dx if i % 2 == 0 else -dx)
        px, py = client_pt(hwnd, fx=x, fy=cy)
        user32.SetCursorPos(px, py)
        time.sleep(wait)


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
    print("waiting plugin/doc...")
    time.sleep(35)

    out = os.path.join(WORK, "_tools")
    cx = 0.5
    cy = 0.5

    # --- scene 1: blank press -> drag onto mesh -> stroke ---
    bx, by = client_pt(hwnd, fx=0.08, fy=cy)
    user32.SetCursorPos(bx, by)
    time.sleep(0.8)
    cap_a = os.path.join(out, "f1_before.bmp")
    capture(hwnd, cap_a)
    send_mouse(0x0002)  # left down at blank
    time.sleep(0.3)
    for i in range(1, 11):
        user32.SetCursorPos(*client_pt(hwnd, fx=0.08 + 0.042 * i, fy=cy))
        time.sleep(0.2)
    # on mesh now, stroke passes
    stroke_pass(hwnd, cx, cy)
    time.sleep(0.5)
    send_mouse(0x0004)  # left up
    time.sleep(0.8)
    cap_b = os.path.join(out, "f1_after.bmp")
    capture(hwnd, cap_b)
    print("S1 blank->mesh bridge diff: %.4f" % diff_ratio(cap_a, cap_b))

    # --- scene 2: direct mesh press -> stroke ---
    mx, my = client_pt(hwnd, fx=cx, fy=cy)
    user32.SetCursorPos(mx, my)
    time.sleep(0.6)
    cap_c = os.path.join(out, "f2_before.bmp")
    capture(hwnd, cap_c)
    send_mouse(0x0002)
    time.sleep(0.2)
    stroke_pass(hwnd, cx, cy)
    time.sleep(0.3)
    send_mouse(0x0004)
    time.sleep(0.8)
    cap_d = os.path.join(out, "f2_after.bmp")
    capture(hwnd, cap_d)
    print("S2 direct mesh stroke diff: %.4f" % diff_ratio(cap_c, cap_d))

    # --- scene 3: ctrl+left drag (mask) ---
    user32.keybd_event(0x11, 0, 0, 0)
    time.sleep(0.2)
    cap_e = os.path.join(out, "f3_before.bmp")
    capture(hwnd, cap_e)
    mx, my = client_pt(hwnd, fx=0.3, fy=0.3)
    user32.SetCursorPos(mx, my)
    send_mouse(0x0002)
    time.sleep(0.2)
    for i in range(1, 9):
        user32.SetCursorPos(*client_pt(hwnd, fx=0.3 + 0.05 * i, fy=0.3 + 0.05 * i))
        time.sleep(0.15)
    send_mouse(0x0004)
    user32.keybd_event(0x11, 0, 0x0002, 0)
    time.sleep(0.8)
    cap_f = os.path.join(out, "f3_after.bmp")
    capture(hwnd, cap_f)
    print("S3 ctrl mask drag diff: %.4f" % diff_ratio(cap_e, cap_f))

    # --- scene 4: right-button rotate ---
    rx, ry = client_pt(hwnd, fx=cx, fy=cy)
    user32.SetCursorPos(rx, ry)
    time.sleep(0.5)
    cap_g = os.path.join(out, "f4_before.bmp")
    capture(hwnd, cap_g)
    send_mouse(0x0008)  # right down
    time.sleep(0.2)
    for i in range(1, 9):
        user32.SetCursorPos(*client_pt(hwnd, fx=0.5 + 0.04 * i, fy=0.5))
        time.sleep(0.15)
    send_mouse(0x0010)  # right up
    time.sleep(0.8)
    cap_h = os.path.join(out, "f4_after.bmp")
    capture(hwnd, cap_h)
    print("S4 rmb rotate diff: %.4f" % diff_ratio(cap_g, cap_h))

    dismiss.terminate()


if __name__ == "__main__":
    main()
