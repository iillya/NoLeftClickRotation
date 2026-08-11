# -*- coding: utf-8 -*-
import ctypes
import re
import sys
import time
from ctypes import wintypes

PID = int(sys.argv[1])
SOURCE = sys.argv[2]
LOG = sys.argv[3]

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
u32 = ctypes.WinDLL("user32", use_last_error=True)
k32.OpenProcess.restype = ctypes.c_void_p
k32.ReadProcessMemory.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
process = k32.OpenProcess(0x410, False, PID)


def log(value):
    with open(LOG, "a", encoding="utf-8") as stream:
        stream.write(value + "\n")
        stream.flush()


def read(address, size):
    buffer = ctypes.create_string_buffer(size)
    received = ctypes.c_size_t()
    if not k32.ReadProcessMemory(
        process, ctypes.c_void_p(address), buffer, size, ctypes.byref(received)
    ) or received.value != size:
        return None
    return buffer.raw


def fresh_comma():
    while u32.GetAsyncKeyState(0xBC) & 0x8000:
        time.sleep(0.005)
    while not (u32.GetAsyncKeyState(0xBC) & 0x8000):
        time.sleep(0.002)
    # Capture logical state before the expensive LightBox redraw settles.
    time.sleep(0.025)


def values(items):
    pages = {}
    for address, _, _ in items:
        page = address & ~0xFFFF
        if page not in pages:
            pages[page] = read(page, 0x10000)
    return {
        address: (pages[address & ~0xFFFF] or b"\xFF" * 0x10000)[address & 0xFFFF]
        for address, _, _ in items
    }


with open(LOG, "w", encoding="utf-8") as stream:
    stream.write("LOADING\n")

items = []
pattern = re.compile(r"^0x([0-9a-f]+) (\d+) (\d+)$")
with open(SOURCE, encoding="utf-8") as stream:
    for line in stream:
        match = pattern.match(line)
        if match:
            items.append(tuple(map(int, (match[1], match[2], match[3]), (16, 10, 10))))

log("READY %d" % len(items))
for cycle in range(1, 5):
    fresh_comma()
    current = values(items)
    expected_index = 2 if cycle % 2 else 1
    items = [item for item in items if current[item[0]] == item[expected_index]]
    log("CYCLE %d %d" % (cycle, len(items)))

for item in items:
    log("%#x %d %d" % item)
log("DONE")
