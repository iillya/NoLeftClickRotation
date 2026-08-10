# -*- coding: utf-8 -*-
"""Auto-test bridge v2: blank-press then drag onto mesh."""

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
LOG = os.path.join(os.environ["TEMP"], "nlr_bridge2.log")
PLUGIN = os.path.join(
    os.environ["APPDATA"],
    r"Maxon\Maxon ZBrush 2026_F3C8B4C4\ZStartup\ZPlugs64\NoLeftClickRotation.py",
)
SRC = os.path.join(WORK, "_tools", "nlc_bridge2.py")

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


class INPUT(ctypes.Structure):
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]
    _anonymous_ = ("mi",)
    _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]


user32.SendInput.restype = wintypes.UINT
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


def send_left(down):
    inp = INPUT()
    inp.type = 0
    inp.mi.dwFlags = 0x0002 if down else 0x0004
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


def client_center(hwnd, fy=0.5, fx=0.5):
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    tl = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    x = tl.x + int(cr.right * fx)
    y = tl.y + int(cr.bottom * fy)
    return x, y


def read_log():
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def capture_bmp(hwnd, path):
    gdi32 = ctypes.WinDLL("gdi32")
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w = r.right - r.left
    h = r.bottom - r.top
    hdc_win = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
    bmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    old = gdi32.SelectObject(hdc_mem, bmp)
    user32.PrintWindow(hwnd, hdc_mem, 0)
    # DIB
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                    ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                    ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = w
    bi.biHeight = h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    got = gdi32.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.SelectObject(hdc_mem, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_win)
    if not got:
        return None
    with open(path, "wb") as f:
        f.write(b"BM")
        f.write(struct.pack("<IHHI", 54 + w * h * 4, 0, 0, 54))
        f.write(struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0, w * h * 4,
                            0, 0, 0, 0))
        f.write(buf.raw)
    return w, h


def diff_ratio(p1, p2):
    with open(p1, "rb") as f1, open(p2, "rb") as f2:
        d1 = f1.read()[54:]
        d2 = f2.read()[54:]
    n = min(len(d1), len(d2))
    diff = 0
    step = 4
    for i in range(0, n, step):
        if d1[i:i+step] != d2[i:i+step]:
            diff += 1
    return diff / max(1, n // step)


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
    print("ZBrush starting...")

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
    print("ZBrush window found, waiting for plugin+doc...")
    time.sleep(30)

    # blank point: left area, drag horizontally onto mesh at center
    bx, by = client_center(hwnd, fx=0.10, fy=0.5)
    mx, my = client_center(hwnd, fx=0.5, fy=0.5)
    print("blank=(%d,%d) mesh=(%d,%d)" % (bx, by, mx, my))

    user32.SetCursorPos(bx, by)
    time.sleep(1.0)
    user32.SetCursorPos(mx, my)
    time.sleep(0.5)
    cap_a = os.path.join(WORK, "_tools", "shot_a.bmp")
    capture_bmp(hwnd, cap_a)
    print("press at blank")
    send_left(True)
    time.sleep(0.5)
    # drag slowly onto mesh
    steps = 12
    for i in range(1, steps + 1):
        x = bx + (mx - bx) * i // steps
        y = by + (my - by) * i // steps
        user32.SetCursorPos(x, y)
        time.sleep(0.25)
    time.sleep(2.0)
    print("hold on mesh, stroke a few passes")
    for i in range(6):
        fx = 0.5 + (0.35 if i % 2 == 0 else -0.35)
        x, y = client_center(hwnd, fx=fx, fy=0.5)
        user32.SetCursorPos(x, y)
        time.sleep(0.3)
    send_left(False)
    time.sleep(0.8)
    cap_b = os.path.join(WORK, "_tools", "shot_b.bmp")
    capture_bmp(hwnd, cap_b)
    ratio = diff_ratio(cap_a, cap_b)
    print("canvas diff ratio after stroke: %.4f" % ratio)
    print("screenshots:", cap_a, cap_b)

    print("=== log tail ===")
    print(read_log()[-4000:])
    dismiss.terminate()


if __name__ == "__main__":
    main()
