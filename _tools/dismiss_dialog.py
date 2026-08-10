# -*- coding: utf-8 -*-
"""自动点掉 ZBrush 的模态对话框（如“最近一次会话异常终止”）。
后台循环运行：找到属于 ZBrush 进程的 #32770 对话框后，点击其按钮关闭。"""

import ctypes
import os
import sys
import time
from ctypes import wintypes

WM_COMMAND = 0x0111
BM_CLICK = 0x00F5
IDOK = 1
TH32CS_SNAPPROCESS = 0x00000002

user32 = ctypes.WinDLL("user32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumChildWindows.restype = wintypes.BOOL
user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

kernel32.GetCurrentProcessId.restype = wintypes.DWORD


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def _zbrush_pids():
    pids = set()
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap and snap != wintypes.HANDLE(-1).value:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if kernel32.Process32FirstW(snap, ctypes.byref(pe)):
            while True:
                if pe.szExeFile.lower() == "zbrush.exe":
                    pids.add(pe.th32ProcessID)
                if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                    break
        kernel32.CloseHandle(snap)
    return pids


def _click_button(button_hwnd):
    user32.SendMessageW(button_hwnd, BM_CLICK, 0, 0)


_found_button = [False]


@WNDENUMPROC
def _enum_button(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, buf, 64)
    if buf.value == "Button" and user32.IsWindowVisible(hwnd):
        _found_button[0] = True
        _click_button(hwnd)
        return False
    return True


@WNDENUMPROC
def _enum_windows(hwnd, lparam):
    buf = ctypes.create_unicode_buffer(256)
    if user32.GetClassNameW(hwnd, buf, 256) and buf.value == "#32770":
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == lparam and user32.IsWindowVisible(hwnd):
            _found_button[0] = False
            user32.EnumChildWindows(hwnd, _enum_button, 0)
            if not _found_button[0]:
                user32.PostMessageW(hwnd, WM_COMMAND, IDOK, 0)
            return False
    return True


def main():
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            pids = _zbrush_pids()
            for pid in pids:
                user32.EnumWindows(_enum_windows, pid)
        except Exception:
            pass
        time.sleep(0.5)


if __name__ == "__main__":
    main()
