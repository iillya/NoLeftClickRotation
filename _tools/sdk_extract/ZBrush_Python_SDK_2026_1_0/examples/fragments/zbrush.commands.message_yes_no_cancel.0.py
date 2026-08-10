"""Code fragment for zbrush.commands.message_yes_no_cancel.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

result: int = zbc.message_yes_no_cancel("Delete all images?", "Please confirm")
print(f"User clicked {'YES' if result == 1 else 'NO' if result == 0 else 'CANCEL'}")
