# -*- coding: utf-8 -*-
"""编排 lambda 抓取测试：
1. 关闭所有 ZBrush；2. 后台启动弹窗点掉器；3. 启动 ZBrush 并打开测试工程；
4. 轮询 nlr_lambda.log；5. 读 ZBrush 内存验证补丁是否生效。
"""

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

WORK = r"C:\Users\liuwenbo\Desktop\zb插件"
ZBRUSH = r"C:\Program Files\Maxon ZBrush 2026\ZBrush.exe"
SCENE = os.path.join(os.environ["TEMP"], "test_scene.zpr")
LOG = os.path.join(os.environ["TEMP"], "nlr_lambda.log")
PLUGIN = os.path.join(
    os.environ["APPDATA"],
    r"Maxon\Maxon ZBrush 2026_F3C8B4C4\ZStartup\ZPlugs64\NoLeftClickRotation.py",
)
CAP_SRC = os.path.join(WORK, "_tools", "nlc_lambda_capture.py")


def stop_zbrush():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-Process -Name ZBrush -ErrorAction SilentlyContinue | Stop-Process -Force"],
        capture_output=True,
    )


def start_zbrush():
    subprocess.Popen([ZBRUSH, SCENE])


def read_log():
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def check_patch(pid):
    PROCESS_VM_READ = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi")
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    kernel32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
        ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t),
    ]
    class MODULEINFO(ctypes.Structure):
        _fields_ = [
            ("lpBaseOfDll", wintypes.LPVOID),
            ("SizeOfImage", wintypes.DWORD),
            ("EntryPoint", wintypes.LPVOID),
        ]
    psapi.EnumProcessModulesEx.restype = wintypes.BOOL
    psapi.EnumProcessModulesEx.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.DWORD,
    ]
    psapi.GetModuleBaseNameW.restype = wintypes.DWORD
    psapi.GetModuleBaseNameW.argtypes = [
        wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD,
    ]
    psapi.GetModuleInformation.restype = wintypes.BOOL
    psapi.GetModuleInformation.argtypes = [
        wintypes.HANDLE, wintypes.HMODULE, ctypes.POINTER(MODULEINFO), wintypes.DWORD,
    ]
    h = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        return "open fail %d" % ctypes.get_last_error()
    buf = (wintypes.HMODULE * 1024)()
    needed = wintypes.DWORD()
    psapi.EnumProcessModulesEx(h, buf, ctypes.sizeof(buf), ctypes.byref(needed), 0x03)
    count = needed.value // ctypes.sizeof(wintypes.HMODULE)
    base = None
    for i in range(count):
        name = ctypes.create_unicode_buffer(260)
        psapi.GetModuleBaseNameW(h, buf[i], name, 260)
        if name.value.lower() == "zbrush.exe":
            mi = MODULEINFO()
            psapi.GetModuleInformation(h, buf[i], ctypes.byref(mi), ctypes.sizeof(mi))
            base = int(mi.lpBaseOfDll)
            break
    if not base:
        return "no zbrush module"
    data = ctypes.create_string_buffer(14)
    got = ctypes.c_size_t(0)
    ok = kernel32.ReadProcessMemory(h, base + 0x1898F90, data, 14, ctypes.byref(got))
    return "patched=%s bytes=%s" % (ok and data.raw.hex().startswith("48b8"), data.raw.hex())


def main():
    # 1. 部署抓取脚本为插件
    import shutil
    shutil.copyfile(CAP_SRC, PLUGIN)
    print("deployed capture plugin")

    # 2. 关掉现有 ZBrush
    stop_zbrush()
    time.sleep(3)
    print("zbrush stopped")

    # 3. 后台启动弹窗点掉器
    dismiss = subprocess.Popen(
        [sys.executable, os.path.join(WORK, "_tools", "dismiss_dialog.py")],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    print("dismiss started")

    # 4. 启动 ZBrush
    start_zbrush()
    print("zbrush starting...")

    # 5. 轮询日志
    last = ""
    for _ in range(60):
        time.sleep(5)
        cur = read_log()
        if cur != last:
            last = cur
            print("--- log ---")
            print(cur)
        if "capture hook OK" in cur:
            break
    print("=== patch check ===")
    for pid in subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process -Name ZBrush -ErrorAction SilentlyContinue).Id"],
        capture_output=True, text=True,
    ).stdout.split():
        print("pid", pid, check_patch(int(pid)))

    dismiss.terminate()


if __name__ == "__main__":
    main()
