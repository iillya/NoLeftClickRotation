# -*- coding: utf-8 -*-
"""测试用输入驱动：向 ZBrush 模拟键盘/鼠标（用于自动验证插件行为）。"""
import ctypes
import time

user32 = ctypes.windll.user32

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_MBUTTON = 0x04
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_F9 = 0x78
VK_N = 0x4E

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040


def move(x, y):
    user32.SetCursorPos(int(x), int(y))


def key(vk, down):
    user32.keybd_event(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0)


def lbtn(down):
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def rbtn(down):
    user32.mouse_event(MOUSEEVENTF_RIGHTDOWN if down else MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


def mbtn(down):
    user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN if down else MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)


def combo(*keys):
    for vk in keys:
        key(vk, True)
    for vk in reversed(keys):
        key(vk, False)


def ctrl_n():
    combo(VK_CONTROL, VK_N)


def drag_circle(cx, cy, radius, steps=48, duration=2.0, hold_f9=True, alt=False):
    """按住（可选 F9/Alt）左键沿圆周拖动，模拟视图旋转/平移。"""
    if hold_f9:
        key(VK_F9, True)
        time.sleep(0.25)
    if alt:
        key(VK_MENU, True)
        time.sleep(0.15)
    move(cx + radius, cy)
    time.sleep(0.2)
    lbtn(True)
    time.sleep(0.15)
    import math
    for i in range(1, steps + 1):
        a = 2 * math.pi * i / steps
        x = cx + radius * math.cos(a)
        y = cy + radius * math.sin(a)
        move(x, y)
        time.sleep(duration / steps)
    lbtn(False)
    time.sleep(0.2)
    if alt:
        key(VK_MENU, False)
    if hold_f9:
        key(VK_F9, False)


def drag_line(x0, y0, x1, y1, steps=40, duration=1.2, hold_f9=True, ctrl=False, alt=False):
    """按住（可选 F9/Ctrl/Alt）左键沿直线拖动。"""
    if hold_f9:
        key(VK_F9, True)
        time.sleep(0.25)
    if ctrl:
        key(VK_CONTROL, True)
        time.sleep(0.15)
    if alt:
        key(VK_MENU, True)
        time.sleep(0.15)
    move(x0, y0)
    time.sleep(0.2)
    lbtn(True)
    time.sleep(0.15)
    for i in range(1, steps + 1):
        t = i / steps
        move(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
        time.sleep(duration / steps)
    lbtn(False)
    time.sleep(0.2)
    if alt:
        key(VK_MENU, False)
    if ctrl:
        key(VK_CONTROL, False)
    if hold_f9:
        key(VK_F9, False)
