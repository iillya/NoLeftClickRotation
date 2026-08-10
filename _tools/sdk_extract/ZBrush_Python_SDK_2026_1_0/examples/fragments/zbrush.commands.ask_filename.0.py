"""Code fragment for zbrush.commands.ask_filename.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Opens a dialog to load a `dxf` or `obj` file.
file: str = zbc.ask_filename("DXF (*.dxf)|*.dxf|OBJ (*.obj)|*.obj||", "","Please select a file to load...")
print(f"Selected file: {file}")
# Opens a dialog to save a file with the `*.zvr` extension and a default name of `tempFile`.
file: str = zbc.ask_filename("*.zvr", "tempFile")
print(f"Selected file: {file}")
