# -*- coding: utf-8 -*-
import os

LOG = os.path.join(os.environ.get("TEMP", os.path.dirname(__file__)),
                   "lightbox_path_probe.log")
BUTTON = "Preferences:LightBox:LightBox"
NAMES = (
    "Projects", "Tools", "Brushes", "Textures", "Alphas", "Materials",
    "Noises", "Fibers", "Arrays", "Meshes", "Docs", "RenderSets",
    "Filters", "QuickSave", "Spotlights", "LightCaps", "Start",
    "New Folder", "Open File", "Maxon", "User",
)


def snapshot(zbc, label):
    with open(LOG, "a", encoding="utf-8") as stream:
        stream.write("--- %s ---\n" % label)
        for root in ("LightBox", "Lightbox"):
            for name in NAMES:
                path = root + ":" + name
                try:
                    exists = bool(zbc.exists(path))
                    flags = int(zbc.get_flags(path)) if exists else -1
                    status = bool(zbc.get_status(path)) if exists else False
                    if exists or flags != -1:
                        stream.write("%s exists=%d flags=%#x status=%d\n" %
                                     (path, int(exists), flags, int(status)))
                except Exception:
                    pass


def main():
    import zbrush.commands as zbc
    with open(LOG, "w", encoding="utf-8") as stream:
        stream.write("=== LightBox dynamic path probe ===\n")
    snapshot(zbc, "A")
    zbc.press(BUTTON)
    snapshot(zbc, "B")
    zbc.press(BUTTON)
    snapshot(zbc, "A2")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        with open(LOG, "a", encoding="utf-8") as stream:
            stream.write("FATAL %r\n" % (error,))
