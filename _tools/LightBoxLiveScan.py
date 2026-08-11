# -*- coding: utf-8 -*-
import ctypes
import sys
import time
from ctypes import wintypes

LOG = sys.argv[2]
PID = int(sys.argv[1])


def log(text):
    with open(LOG, "a", encoding="utf-8") as stream:
        stream.write(text + "\n")
        stream.flush()


class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("PartitionId", wintypes.WORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]


k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
k32.OpenProcess.restype = ctypes.c_void_p
k32.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
process = k32.OpenProcess(0x410, False, PID)


def read(address, size):
    buffer = ctypes.create_string_buffer(size)
    received = ctypes.c_size_t()
    ok = k32.ReadProcessMemory(
        process, ctypes.c_void_p(address), buffer, size,
        ctypes.byref(received),
    )
    if not ok or received.value != size:
        return None
    return buffer.raw


def wait_comma(number):
    # Ignore a key that was already held while the (slow) initial snapshot ran.
    # A capture must begin with a confirmed key-up state and then a fresh edge.
    while u32.GetAsyncKeyState(0xBC) & 0x8000:
        time.sleep(0.01)
    was_down = False
    deadline = time.time() + 180
    while time.time() < deadline:
        down = bool(u32.GetAsyncKeyState(0xBC) & 0x8000)
        if down and not was_down:
            time.sleep(0.75)
            log("CAPTURE %d" % number)
            return
        was_down = down
        time.sleep(0.01)
    raise TimeoutError("comma %d timeout" % number)


def main():
    with open(LOG, "w", encoding="utf-8") as stream:
        stream.write("SNAPSHOTTING\n")

    chunks = []
    address = 0
    info = MBI()
    allowed = {0x04, 0x08, 0x40, 0x80}
    while address < 0x7FFF00000000:
        if not k32.VirtualQueryEx(
            process, ctypes.c_void_p(address), ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            break
        base = int(info.BaseAddress or 0)
        size = int(info.RegionSize)
        protection = info.Protect & 0xFF
        if (
            info.State == 0x1000 and info.Type == 0x20000
            and protection in allowed and not (info.Protect & 0x100)
        ):
            for offset in range(0, size, 0x10000):
                length = min(0x10000, size - offset)
                data = read(base + offset, length)
                if data is not None:
                    chunks.append((base + offset, data))
        address = max(address + 0x1000, base + size)

    log("READY %d" % len(chunks))
    wait_comma(1)
    candidates = []
    for base, before in chunks:
        after = read(base, len(before))
        if after is not None and after != before:
            candidates.extend(
                (base + index, left, right)
                for index, (left, right) in enumerate(zip(before, after))
                if left != right
            )
    log("A_B %d" % len(candidates))

    wait_comma(2)
    candidates = [
        item for item in candidates
        if (read(item[0], 1) or b"\xFF")[0] == item[1]
    ]
    log("A2 %d" % len(candidates))
    wait_comma(3)
    candidates = [
        item for item in candidates
        if (read(item[0], 1) or b"\xFF")[0] == item[2]
    ]
    log("B2 %d" % len(candidates))
    wait_comma(4)
    candidates = [
        item for item in candidates
        if (read(item[0], 1) or b"\xFF")[0] == item[1]
    ]
    log("A3 %d" % len(candidates))
    for address, closed, opened in candidates:
        log("%#x %d %d" % (address, closed, opened))
    log("DONE")


try:
    main()
except Exception as error:
    log("FATAL %r" % (error,))
