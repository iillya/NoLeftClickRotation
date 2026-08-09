# -*- coding: utf-8 -*-
"""Read-only cursor probe: logs Windows cursor identity + button state.

This tool does NOT touch ZBrush. It only reads system-wide cursor state so we
can verify whether ZBrush distinguishes "canvas" (hidden/custom cursor) from
"UI" (standard arrow/hand/... cursor) without using any undocumented API.
"""

import ctypes
import ctypes.wintypes
import os
import sys
import time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cursor_probe.log")
STOP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cursor_probe.stop")

user32 = ctypes.windll.user32


class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("hCursor", ctypes.wintypes.HANDLE),
        ("ptScreenPos", ctypes.wintypes.POINT),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


STD_IDS = {
    32512: "arrow",
    32513: "ibeam",
    32514: "wait",
    32515: "cross",
    32516: "uparrow",
    32642: "sizenwse",
    32643: "sizenesw",
    32644: "sizewe",
    32645: "sizens",
    32646: "sizeall",
    32648: "no",
    32649: "hand",
    32650: "appstarting",
    32651: "help",
    32671: "pin",
    32672: "person",
}


def std_cursor_handles():
    out = {}
    for ident, name in STD_IDS.items():
        h = user32.LoadCursorW(None, ctypes.c_void_p(ident))
        if h:
            out[h] = name
    return out


def cursor_name(handle, std_map):
    if not handle:
        return "NULL(hidden)"
    name = std_map.get(handle)
    if name:
        return name
    return "custom:%d" % handle


def log_line(line):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    try:
        if os.path.exists(OUT):
            os.remove(OUT)
        if os.path.exists(STOP):
            os.remove(STOP)
    except Exception:
        pass

    std_map = std_cursor_handles()
    hwnd = user32.FindWindowW("ZBrush", None)
    rect = RECT()
    has_rect = False
    if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        has_rect = True

    log_line("probe_start hwnd=%s win_rect=[%d,%d,%d,%d]" % (
        hwnd,
        rect.left, rect.top, rect.right, rect.bottom,
    ) if has_rect else "probe_start hwnd=None")

    last_key = None
    last_mark = {k: 0 for k in (0x71, 0x72, 0x73, 0x74)}  # F2..F5
    mark_names = {0x71: "MARK blank(F2)", 0x72: "MARK mesh(F3)",
                  0x73: "MARK slider(F4)", 0x74: "MARK button(F5)"}
    start = time.time()
    while True:
        if os.path.exists(STOP):
            log_line("probe_stop requested")
            break
        if time.time() - start > 1800:  # 30 min safety cap
            log_line("probe_stop timeout")
            break

        for vk in last_mark:
            pressed = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and time.time() - last_mark[vk] > 0.8:
                last_mark[vk] = time.time()
                log_line("t=%.3f %s" % (time.time() - start, mark_names[vk]))

        ci = CURSORINFO()
        ci.cbSize = ctypes.sizeof(CURSORINFO)
        ok = user32.GetCursorInfo(ctypes.byref(ci))
        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        left_down = bool(user32.GetAsyncKeyState(0x01) & 0x8000)

        pos = (pt.x, pt.y)
        if ok:
            key = (pos, int(ci.hCursor or 0), int(ci.flags), left_down)
        else:
            key = (pos, 0, -1, left_down)
        if key != last_key:
            last_key = key
            if ok:
                name = cursor_name(ci.hCursor, std_map)
                log_line("t=%.3f pos=%d,%d flags=%d cursor=%s left=%d" % (
                    time.time() - start, pt.x, pt.y, ci.flags, name, int(left_down)))
            else:
                log_line("t=%.3f pos=%d,%d getcursorinfo_failed left=%d" % (
                    time.time() - start, pt.x, pt.y, int(left_down)))
        time.sleep(0.015)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        with open(OUT, "a", encoding="utf-8") as f:
            f.write("probe_error %r\n" % (exc,))
        raise
