# -*- coding: utf-8 -*-
"""Fully automatic lambda-capture test.

1. deploy capture plugin, restart ZBrush with the test scene
2. wait for hook install + document ready
3. auto-detect a mesh point and a blank point in the canvas
4. sample idle, then hold left button on blank, then hold on mesh
5. compare the sampled lambda ring buffer before/after each hold
"""

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
LOG = os.path.join(os.environ["TEMP"], "nlr_real.log")
PLUGIN = os.path.join(
    os.environ["APPDATA"],
    r"Maxon\Maxon ZBrush 2026_F3C8B4C4\ZStartup\ZPlugs64\NoLeftClickRotation.py",
)
CAP_SRC = os.path.join(WORK, "_tools", "nlc_real_capture.py")
DISMISS = os.path.join(WORK, "_tools", "dismiss_dialog.py")

user32 = ctypes.WinDLL("user32")


# ---------- windows helpers ----------
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HANDLE,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.SetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.MoveWindow.restype = wintypes.BOOL
user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.EnumDisplayMonitors.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                       MONITORENUMPROC, wintypes.LPARAM]


def find_zbrush_window():
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


def get_monitors():
    out = []

    @MONITORENUMPROC
    def cb(hmon, hdc, rect, lp):
        out.append((rect.contents.left, rect.contents.top,
                    rect.contents.right, rect.contents.bottom))
        return True

    user32.EnumDisplayMonitors(None, None, cb, 0)
    return out


def move_to_second_monitor(hwnd):
    mons = get_monitors()
    if len(mons) < 2:
        return
    m = mons[1]
    w = m[2] - m[0]
    h = m[3] - m[1]
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    ww = r.right - r.left
    wh = r.bottom - r.top
    user32.MoveWindow(hwnd, m[0] + (w - ww) // 2, m[1] + (h - wh) // 2, ww, wh, True)
    time.sleep(0.5)


def client_rect(hwnd):
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    tl = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(tl))
    return tl.x, tl.y, tl.x + cr.right, tl.y + cr.bottom


def send_left(down):
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]
    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]
    inp = INPUT()
    inp.type = 0
    inp.mi.dwFlags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


# ---------- zbrush process helpers ----------
def stop_zbrush():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process -Name ZBrush -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True,
    )
    time.sleep(3)


def read_log():
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def parse_report(line):
    m = re.search(
        r"xy=([-\d.]+),([-\d.]+) mat=(\S+) down=(\d) count=(\d+) uniq=(\S+) last=([0-9a-fx]+)",
        line,
    )
    if not m:
        return None
    return {
        "x": float(m.group(1)), "y": float(m.group(2)),
        "mat": m.group(3), "down": int(m.group(4)),
        "count": int(m.group(5)),
        "uniq": m.group(6), "last": m.group(7),
    }


def wait_for(pred, timeout, desc):
    t0 = time.time()
    last = ""
    while time.time() - t0 < timeout:
        cur = read_log()
        if cur != last:
            last = cur
            for line in cur.splitlines()[-8:]:
                if "xy=" in line or "err" in line or "FAIL" in line:
                    print("  |", line)
        if pred(cur):
            return True
        time.sleep(2)
    return False


def sample_at(hwnd, sx, sy, hold_sec=0.0, label=""):
    user32.SetCursorPos(sx, sy)
    time.sleep(0.8)
    if hold_sec > 0:
        send_left(True)
        print("  holding LEFT at %s (%d,%d) for %.1fs" % (label, sx, sy, hold_sec))
        time.sleep(hold_sec)
        send_left(False)
        time.sleep(0.5)
    else:
        print("  idle at %s (%d,%d)" % (label, sx, sy))
        time.sleep(1.5)


def current_report():
    for line in reversed(read_log().splitlines()):
        r = parse_report(line)
        if r:
            return r
    return None


def find_mesh_point(hwnd):
    x0, y0, x1, y1 = client_rect(hwnd)
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    candidates = [
        (cx, cy), (cx, cy - 120), (cx, cy + 120),
        (cx - 150, cy), (cx + 150, cy),
    ]
    for px, py in candidates:
        sample_at(hwnd, px, py, 0, "probe")
        r = current_report()
        if r and r["mat"] not in ("0.0", "0", "None"):
            print("  mesh point found at (%d,%d) mat=%s xy=(%.0f,%.0f)"
                  % (px, py, r["mat"], r["x"], r["y"]))
            return px, py
    return None


def find_blank_point(hwnd, mesh_pt):
    x0, y0, x1, y1 = client_rect(hwnd)
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    candidates = [
        (cx, y0 + int((y1 - y0) * 0.12)),
        (cx, y0 + int((y1 - y0) * 0.85)),
        (x0 + int((x1 - x0) * 0.12), cy),
        (x0 + int((x1 - x0) * 0.85), cy),
    ]
    for px, py in candidates:
        if abs(px - mesh_pt[0]) < 30 and abs(py - mesh_pt[1]) < 30:
            continue
        sample_at(hwnd, px, py, 0, "probe")
        r = current_report()
        if r and r["mat"] in ("0.0", "0"):
            print("  blank point found at (%d,%d) mat=%s xy=(%.0f,%.0f)"
                  % (px, py, r["mat"], r["x"], r["y"]))
            return px, py
    return None


def main():
    shutil.copyfile(CAP_SRC, PLUGIN)
    print("1. capture plugin deployed")

    stop_zbrush()
    print("2. ZBrush stopped")

    dismiss = subprocess.Popen(
        [sys.executable, DISMISS], creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.Popen([ZBRUSH, SCENE])
    print("3. ZBrush starting with test scene")

    def hooked_and_ready(cur):
        return ("capture hook OK" in cur and "xy=" in cur
                and "count=14757395258967641292" not in cur)

    if not wait_for(hooked_and_ready, 120, "hook+doc"):
        print("TIMEOUT waiting for hook/doc. Last log:")
        print(read_log()[-3000:])
        dismiss.terminate()
        return

    hwnd = find_zbrush_window()
    if not hwnd:
        print("no ZBrush window")
        dismiss.terminate()
        return
    move_to_second_monitor(hwnd)
    hwnd = find_zbrush_window()
    print("4. ZBrush window ready, hook OK")

    mesh = find_mesh_point(hwnd)
    blank = find_blank_point(hwnd, mesh) if mesh else None
    if not mesh or not blank:
        print("could not locate mesh/blank points; mesh=%r blank=%r" % (mesh, blank))
        dismiss.terminate()
        return

    r0 = current_report()
    print("5. idle baseline: count=%d uniq=%s" % (r0["count"], r0["uniq"]))

    sample_at(hwnd, blank[0], blank[1], 3.0, "blank hold")
    r1 = current_report()
    print("6. after BLANK hold: count=%d uniq=%s" % (r1["count"], r1["uniq"]))

    sample_at(hwnd, mesh[0], mesh[1], 3.0, "mesh hold")
    r2 = current_report()
    print("7. after MESH hold: count=%d uniq=%s" % (r2["count"], r2["uniq"]))

    print("8. idle again (3s)")
    time.sleep(3)
    r3 = current_report()
    print("9. idle after: count=%d uniq=%s" % (r3["count"], r3["uniq"]))

    print("=== summary ===")
    for name, r in [("baseline", r0), ("blank-hold", r1), ("mesh-hold", r2), ("idle-again", r3)]:
        print("%-12s count=%d uniq=%s" % (name, r["count"], r["uniq"]))
    dismiss.terminate()


if __name__ == "__main__":
    main()
