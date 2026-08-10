"""Code fragment for zbrush.commands.get_keyframes_count.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Enable the Color track and count the keyframes in it.
zbc.set("Movie:TimeLine Tracks:Color", True)
count: int = zbc.get_keyframes_count()
print(f"The Color track has {count} keyframes.")