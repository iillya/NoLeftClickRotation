"""Code fragment for zbrush.commands.get_status.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

status: bool = zbc.get_status("Transform:Move")
print(f"Transform:Move status is: {status}")
