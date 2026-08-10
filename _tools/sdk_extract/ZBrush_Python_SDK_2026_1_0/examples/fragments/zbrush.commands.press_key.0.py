"""Code fragment for zbrush.commands.press_key.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc
import sys

# Press the 'e' key to enabled the 'Scale' transform mode.
zbc.press_key("e", lambda: print("Scale mode enabled"))

# Press 'ctrl+z' to undo the last action on Windows or 'cmd+z' on macOS.
zbc.press_key("CTRL+z" if sys.platform == "win32" else "CMD+z")

# And finally, we can also simulate a key press while executing a function. Here we
# simulate pressing 'N' while creating a new document. This has the effect that we
# will automatically answer a possibly shown question dialog asking us if we want
# to save the current document with 'No'.
zbc.press_key("N", lambda: zbc.press("Document:New Document"))