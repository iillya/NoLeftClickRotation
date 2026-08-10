"""Code fragment for zbrush.commands.get_subtool_status.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the status of the active sub-tool and test the flags which are set on it.
status: int = zbc.get_subtool_status()
print(f"Active sub-tool 'is-visible-subtool' state: {bool(status & 0x0001)}")
print(f"Active sub-tool 'is-visible-folder' state: {bool(status & 0x0002)}")
print(f"Active sub-tool 'volume-add' state: {bool(status & 0x0010)}")
print(f"Active sub-tool 'volume-sub' state: {bool(status & 0x0020)}")
print(f"Active sub-tool 'volume-clip' state: {bool(status & 0x0040)}")
print(f"Active sub-tool 'volume-start' state: {bool(status & 0x0080)}")
print(f"Active sub-tool 'is-closed-folder' state: {bool(status & 0x0400)}")
print(f"Active sub-tool 'is-open-folder' state: {bool(status & 0x0800)}")
