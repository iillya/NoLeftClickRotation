# -*- coding: utf-8 -*-
"""Find ZBrush image globals that toggle with the LightBox overlay."""

import ctypes
import os
import struct
import time


PATH = "Preferences:LightBox:LightBox"
LOG = os.path.join(os.environ.get("TEMP", os.path.dirname(__file__)),
                   "lightbox_memory_probe.log")
CHUNK = 0x10000
WRITE = 0x80000000

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetModuleHandleW.restype = ctypes.c_void_p


def log(text):
    with open(LOG, "a", encoding="utf-8") as stream:
        stream.write(text + "\n")


def writable_sections(base):
    e_lfanew = struct.unpack("<I", ctypes.string_at(base + 0x3C, 4))[0]
    nt = base + e_lfanew
    count = struct.unpack("<H", ctypes.string_at(nt + 6, 2))[0]
    optional_size = struct.unpack("<H", ctypes.string_at(nt + 20, 2))[0]
    table = nt + 24 + optional_size
    result = []
    for index in range(count):
        header = ctypes.string_at(table + index * 40, 40)
        name = header[:8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, rva = struct.unpack_from("<II", header, 8)
        characteristics = struct.unpack_from("<I", header, 36)[0]
        if characteristics & WRITE:
            result.append((name, rva, virtual_size))
    return result


def changed_bytes(address, original):
    changed = []
    size = len(original)
    for offset in range(0, size, CHUNK):
        length = min(CHUNK, size - offset)
        current = ctypes.string_at(address + offset, length)
        before = original[offset:offset + length]
        if current == before:
            continue
        changed.extend(
            offset + index
            for index, (left, right) in enumerate(zip(before, current))
            if left != right
        )
    return changed


def main():
    import zbrush.commands as zbc

    with open(LOG, "w", encoding="utf-8") as stream:
        stream.write("=== LightBox memory differential probe ===\n")
    base = int(kernel32.GetModuleHandleW(None) or 0)
    log("base=%#x" % base)

    all_candidates = []
    snapshots = []
    for name, rva, size in writable_sections(base):
        log("snapshot %s rva=%#x size=%#x" % (name, rva, size))
        snapshots.append((name, rva, ctypes.string_at(base + rva, size)))

    # State A -> toggled state B.
    zbc.press(PATH)
    for name, rva, original in snapshots:
        address = base + rva
        for offset in changed_bytes(address, original):
            before = original[offset]
            after = ctypes.c_ubyte.from_address(address + offset).value
            if before in (0, 1) and after in (0, 1):
                all_candidates.append((rva + offset, before, after))
    log("boolean_changes_A_B=%d" % len(all_candidates))

    # Return to A and retain only exact round trips.
    zbc.press(PATH)
    round_trip = []
    for rva, before, after in all_candidates:
        if ctypes.c_ubyte.from_address(base + rva).value == before:
            round_trip.append((rva, before, after))
    log("round_trip_candidates=%d" % len(round_trip))

    # Toggle once more and demand the same B value, then restore A.
    zbc.press(PATH)
    repeated = []
    for rva, before, after in round_trip:
        if ctypes.c_ubyte.from_address(base + rva).value == after:
            repeated.append((rva, before, after))
    zbc.press(PATH)

    log("repeated_candidates=%d" % len(repeated))
    for rva, before, after in repeated[:2000]:
        log("rva=%#x A=%d B=%d context=%s" % (
            rva,
            before,
            after,
            ctypes.string_at(base + max(0, rva - 16), 33).hex(),
        ))
    zbc.set_notebar_text("LightBox memory probe complete: %d candidates" % len(repeated))


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        try:
            log("FATAL " + repr(exception))
        except Exception:
            pass
