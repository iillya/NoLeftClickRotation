"""Code fragment for zbrush.commands.message_yes_no.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

result: bool = zbc.message_ok_cancel("Delete all images?", "Please confirm")
print(f"User clicked {'YES' if result else 'NO'}")
