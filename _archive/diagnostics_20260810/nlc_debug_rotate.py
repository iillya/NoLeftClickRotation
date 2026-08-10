# -*- coding: utf-8 -*-
"""程序化调试器：定位 ZBrush 视图旋转角度的写入函数。

原理：
1. 附加到 ZBrush（DebugActiveProcess）。
2. 在事件处理器入口（RVA 0x180A0F0）下硬件执行断点（DR0）。
3. 命中后从 RCX 读取事件对象，解析视图角度地址 [obj+0x1B8]+0x3C。
4. 把 DR0 改成对该地址的硬件写断点。
5. 用户右键旋转时命中写断点，记录写入指令的 RIP → 即旋转函数。
"""

import ctypes
import ctypes.wintypes as wintypes
import os
import struct
import sys
import time

LOG = r"C:\Users\liuwenbo\AppData\Local\Temp\nlr_debug.log"

EVENT_PROC_RVA = 0x180A0F0

DBG_CONTINUE = 0x2
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXCEPTION_DEBUG_EVENT = 1
CREATE_PROCESS_DEBUG_EVENT = 3
CREATE_THREAD_DEBUG_EVENT = 2
EXIT_PROCESS_DEBUG_EVENT = 5
EXCEPTION_SINGLE_STEP = 0x80000004
STATUS_BREAKPOINT = 0x80000003

THREAD_GET_CONTEXT = 0x0002
THREAD_SET_CONTEXT = 0x0020
PROCESS_ALL_ACCESS = 0x1F0FFF

CONTEXT_AMD64 = 0x100000
CONTEXT_CONTROL = CONTEXT_AMD64 | 0x1
CONTEXT_INTEGER = CONTEXT_AMD64 | 0x2
CONTEXT_SEGMENTS = CONTEXT_AMD64 | 0x4
CONTEXT_FLOATING_POINT = CONTEXT_AMD64 | 0x8
CONTEXT_DEBUG_REGISTERS = CONTEXT_AMD64 | 0x10
CONTEXT_ALL = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_SEGMENTS | CONTEXT_FLOATING_POINT | CONTEXT_DEBUG_REGISTERS

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
n32 = ctypes.WinDLL("ntdll", use_last_error=True)


class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [
        ("ExceptionCode", wintypes.DWORD),
        ("ExceptionFlags", wintypes.DWORD),
        ("ExceptionRecord", ctypes.c_void_p),
        ("ExceptionAddress", ctypes.c_void_p),
        ("NumberParameters", wintypes.DWORD),
        ("ExceptionInformation", ctypes.c_void_p * 15),
    ]


class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [
        ("Exception", EXCEPTION_RECORD),
        ("raw", ctypes.c_byte * 0xC0),
    ]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [
        ("dwDebugEventCode", wintypes.DWORD),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
        ("u", DEBUG_EVENT_UNION),
    ]


class CONTEXT(ctypes.Structure):
    _fields_ = [
        ("P1Home", ctypes.c_uint64), ("P2Home", ctypes.c_uint64),
        ("P3Home", ctypes.c_uint64), ("P4Home", ctypes.c_uint64),
        ("P5Home", ctypes.c_uint64), ("P6Home", ctypes.c_uint64),
        ("ContextFlags", wintypes.DWORD), ("MxCsr", wintypes.DWORD),
        ("SegCs", wintypes.DWORD), ("SegDs", wintypes.DWORD),
        ("SegEs", wintypes.DWORD), ("SegFs", wintypes.DWORD),
        ("SegGs", wintypes.DWORD), ("SegSs", wintypes.DWORD),
        ("EFlags", wintypes.DWORD),
        ("Dr0", ctypes.c_uint64), ("Dr1", ctypes.c_uint64),
        ("Dr2", ctypes.c_uint64), ("Dr3", ctypes.c_uint64),
        ("Dr6", ctypes.c_uint64), ("Dr7", ctypes.c_uint64),
        ("Rax", ctypes.c_uint64), ("Rcx", ctypes.c_uint64),
        ("Rdx", ctypes.c_uint64), ("Rbx", ctypes.c_uint64),
        ("Rsp", ctypes.c_uint64), ("Rbp", ctypes.c_uint64),
        ("Rsi", ctypes.c_uint64), ("Rdi", ctypes.c_uint64),
        ("R8", ctypes.c_uint64), ("R9", ctypes.c_uint64),
        ("R10", ctypes.c_uint64), ("R11", ctypes.c_uint64),
        ("R12", ctypes.c_uint64), ("R13", ctypes.c_uint64),
        ("R14", ctypes.c_uint64), ("R15", ctypes.c_uint64),
        ("Rip", ctypes.c_uint64),
    ]


k32.DebugActiveProcess.restype = wintypes.BOOL
k32.DebugActiveProcess.argtypes = [wintypes.DWORD]
k32.DebugActiveProcessStop.restype = wintypes.BOOL
k32.DebugActiveProcessStop.argtypes = [wintypes.DWORD]
k32.WaitForDebugEvent.restype = wintypes.BOOL
k32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT), wintypes.DWORD]
k32.ContinueDebugEvent.restype = wintypes.BOOL
k32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.OpenThread.restype = wintypes.HANDLE
k32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.CloseHandle.restype = wintypes.BOOL
k32.CloseHandle.argtypes = [wintypes.HANDLE]
k32.GetCurrentProcess.restype = wintypes.HANDLE
k32.GetCurrentProcess.argtypes = []
k32.GetThreadContext.restype = wintypes.BOOL
k32.GetThreadContext.argtypes = [wintypes.HANDLE, ctypes.POINTER(CONTEXT)]
k32.SetThreadContext.restype = wintypes.BOOL
k32.SetThreadContext.argtypes = [wintypes.HANDLE, ctypes.POINTER(CONTEXT)]
k32.SuspendThread.restype = wintypes.DWORD
k32.SuspendThread.argtypes = [wintypes.HANDLE]
k32.ResumeThread.restype = wintypes.DWORD
k32.ResumeThread.argtypes = [wintypes.HANDLE]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.restype = wintypes.BOOL
k32.WriteProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]


def _enable_debug_privilege():
    try:
        adv = ctypes.WinDLL("advapi32", use_last_error=True)
        TOKEN_ADJUST_PRIVILEGES = 0x20
        TOKEN_QUERY = 0x8
        SE_PRIVILEGE_ENABLED = 0x2
        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", ctypes.c_long)]
        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]
        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]
        adv.OpenProcessToken.restype = wintypes.BOOL
        adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        adv.LookupPrivilegeValueW.restype = wintypes.BOOL
        adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(LUID)]
        adv.AdjustTokenPrivileges.restype = wintypes.BOOL
        adv.AdjustTokenPrivileges.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]
        h = wintypes.HANDLE()
        if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(h)):
            return False
        luid = LUID()
        if not adv.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
            return False
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        adv.AdjustTokenPrivileges(h, False, ctypes.byref(tp), 0, None, None)
        return True
    except Exception:
        return False


def _log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _read_mem(hproc, addr, size):
    buf = ctypes.create_string_buffer(size)
    n = ctypes.c_size_t()
    if k32.ReadProcessMemory(hproc, ctypes.c_void_p(addr), buf, size, ctypes.byref(n)):
        return buf.raw
    return None


def _read_u64(hproc, addr):
    raw = _read_mem(hproc, addr, 8)
    return struct.unpack("<Q", raw)[0] if raw else None


def _read_u32(hproc, addr):
    raw = _read_mem(hproc, addr, 4)
    return struct.unpack("<I", raw)[0] if raw else None


def _thread_context(tid):
    h = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_SET_CONTEXT, False, tid)
    if not h:
        return None
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_ALL
    ok = k32.GetThreadContext(h, ctypes.byref(ctx))
    k32.CloseHandle(h)
    return ctx if ok else None


def _set_debug_regs(tid, dr0, dr7):
    h = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_SET_CONTEXT, False, tid)
    if not h:
        return False
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_ALL
    ok = k32.GetThreadContext(h, ctypes.byref(ctx))
    if ok:
        ctx.Dr0 = dr0
        ctx.Dr1 = 0
        ctx.Dr2 = 0
        ctx.Dr3 = 0
        ctx.Dr6 = 0
        ctx.Dr7 = dr7
        ctx.ContextFlags = CONTEXT_ALL
        ok = k32.SetThreadContext(h, ctypes.byref(ctx))
    k32.CloseHandle(h)
    return ok


def _arm_all_threads(pid, dr0, dr7):
    """进程运行时给所有线程设置硬件断点（挂起->设->恢复）。"""
    errs = []
    try:
        class THREADENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", ctypes.c_long),
                ("tpDeltaPri", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
            ]
        TH32CS_SNAPTHREAD = 0x4
        k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k32.Thread32First.restype = wintypes.BOOL
        k32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
        k32.Thread32Next.restype = wintypes.BOOL
        k32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if not snap or snap == wintypes.HANDLE(-1).value:
            return 0
        te = THREADENTRY32()
        te.dwSize = ctypes.sizeof(THREADENTRY32)
        n = 0
        if k32.Thread32First(snap, ctypes.byref(te)):
            while True:
                if te.th32OwnerProcessID == pid:
                    h = k32.OpenThread(THREAD_GET_CONTEXT | THREAD_SET_CONTEXT | 0x4, False, te.th32ThreadID)
                    if h:
                        k32.SuspendThread(h)
                        ctx = CONTEXT()
                        ctx.ContextFlags = CONTEXT_ALL
                        if k32.GetThreadContext(h, ctypes.byref(ctx)):
                            ctx.Dr0 = dr0
                            ctx.Dr1 = 0
                            ctx.Dr2 = 0
                            ctx.Dr3 = 0
                            ctx.Dr6 = 0
                            ctx.Dr7 = dr7
                            ctx.ContextFlags = CONTEXT_ALL
                            if k32.SetThreadContext(h, ctypes.byref(ctx)):
                                n += 1
                            else:
                                errs.append("setctx e%d" % ctypes.get_last_error())
                        else:
                            errs.append("getctx e%d" % ctypes.get_last_error())
                        k32.ResumeThread(h)
                        k32.CloseHandle(h)
                if not k32.Thread32Next(snap, ctypes.byref(te)):
                    break
        k32.CloseHandle(snap)
    except Exception:
        return 0
    if errs:
        _log("  arm errors: %s" % ", ".join(errs[:10]))
    return n


def _module_base(pid):
    """用工具帮助快照读 ZBrush.exe 模块基址。"""
    try:
        class MODULEENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD),
                ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wintypes.DWORD),
                ("hModule", wintypes.HANDLE),
                ("szModule", ctypes.c_wchar * 256),
                ("szExePath", ctypes.c_wchar * 260),
            ]
        TH32CS_SNAPMODULE = 0x00000008
        k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        k32.Module32FirstW.restype = wintypes.BOOL
        k32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
        k32.Module32NextW.restype = wintypes.BOOL
        k32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
        snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
        if not snap or snap == wintypes.HANDLE(-1).value:
            return None
        me = MODULEENTRY32W()
        me.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if k32.Module32FirstW(snap, ctypes.byref(me)):
            base = int(me.modBaseAddr)
            k32.CloseHandle(snap)
            return base
        k32.CloseHandle(snap)
    except Exception:
        pass
    return None


def _find_pid():
    for _ in range(120):
        try:
            out = os.popen("powershell -NoProfile -Command \"(Get-Process ZBrush -ErrorAction SilentlyContinue | Select-Object -First 1).Id\"").read().strip()
            if out.isdigit():
                return int(out)
        except Exception:
            pass
        time.sleep(0.5)
    return None


def main():
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("=== 旋转函数定位 ===\n")
    _enable_debug_privilege()
    _log("等待 ZBrush 启动...")
    pid_env = os.environ.get("NLCDBG_PID")
    pid = int(pid_env) if pid_env and pid_env.isdigit() else _find_pid()
    if not pid:
        _log("FAIL 未找到 ZBrush 进程")
        return
    _log("ZBrush pid=%d" % pid)
    base = _module_base(pid)
    if not base:
        base = 0x140000000
    _log("module base=%#x" % base)
    override = os.environ.get("NLCDBG_EXEC")
    if override:
        proc_addr = int(override, 16)
        _log("override exec addr=%#x" % proc_addr)
    else:
        proc_addr = base + EVENT_PROC_RVA

    hproc = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hproc:
        _log("FAIL OpenProcess err=%d" % ctypes.get_last_error())
        return
    if not k32.DebugActiveProcess(pid):
        _log("FAIL DebugActiveProcess err=%d" % ctypes.get_last_error())
        k32.CloseHandle(hproc)
        return
    _log("已附加。等待进程运行后布执行断点...")

    angle_addr = 0
    state = "ARMING"
    deadline = time.time() + 240
    last_continue = 0.0
    try:
        while time.time() < deadline:
            de = DEBUG_EVENT()
            if not k32.WaitForDebugEvent(ctypes.byref(de), 1000):
                if state == "ARMING" and last_continue and time.time() - last_continue > 0.5:
                    n = _arm_all_threads(pid, proc_addr, 0x1)
                    _log("执行断点布到 %d 个线程 —— 请右键旋转" % n)
                    state = "EXEC_BP"
                continue
            code = de.dwDebugEventCode
            status = DBG_CONTINUE
            if code == CREATE_THREAD_DEBUG_EVENT and state != "DONE":
                # 新线程创建（已停住）：顺手布执行断点
                if state == "EXEC_BP":
                    _set_debug_regs(de.dwThreadId, proc_addr, 0x1)
            if code == EXCEPTION_DEBUG_EVENT:
                exc_code = de.u.Exception.ExceptionCode
                if exc_code == EXCEPTION_SINGLE_STEP:
                    ctx = _thread_context(de.dwThreadId)
                    if ctx:
                        dr6 = ctx.Dr6
                        rip = ctx.Rip
                        if state == "EXEC_BP" and (dr6 & 1) and rip == proc_addr:
                            obj = ctx.Rcx
                            sub = _read_u64(hproc, obj + 0x1B8)
                            _log("命中事件处理器 obj=%#x sub=%#x" % (obj, sub or 0))
                            if sub:
                                angle_addr = sub + 0x3C
                                # DR0 = 写断点（8 字节，RW=写，LEN=10 -> DR7=0x90001）
                                if _set_debug_regs(de.dwThreadId, angle_addr, 0x90001):
                                    state = "WRITE_BP"
                                    _log("已布写断点 angle_addr=%#x —— 请继续右键旋转" % angle_addr)
                                else:
                                    _log("FAIL 设置写断点")
                                    state = "DONE"
                        elif state == "WRITE_BP" and (dr6 & 1):
                            val = _read_u64(hproc, angle_addr)
                            _log(">>> 写入命中! RIP=%#x rva=%#x 角度值=%#x" % (rip, rip - base, val or 0))
                            raw = _read_mem(hproc, rip - 16, 32)
                            if raw:
                                _log(">>> RIP 前 16 字节: %s" % raw[:16].hex())
                                _log(">>> RIP 后 16 字节: %s" % raw[16:].hex())
                            _set_debug_regs(de.dwThreadId, 0, 0)
                            state = "DONE"
                    status = DBG_CONTINUE
                else:
                    status = DBG_EXCEPTION_NOT_HANDLED
            if code == EXIT_PROCESS_DEBUG_EVENT:
                _log("ZBrush 退出")
                break
            k32.ContinueDebugEvent(de.dwProcessId, de.dwThreadId, status)
            last_continue = time.time()
            if state == "DONE":
                break
    finally:
        try:
            k32.DebugActiveProcessStop(pid)
        except Exception:
            pass
        k32.CloseHandle(hproc)
    _log("结束（state=%s）" % state)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write("FATAL %r\n" % (e,))
        except Exception:
            pass
