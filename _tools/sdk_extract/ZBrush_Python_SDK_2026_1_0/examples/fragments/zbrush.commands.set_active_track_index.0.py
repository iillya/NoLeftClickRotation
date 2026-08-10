"""Code fragment for zbrush.commands.set_active_track_index.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# get/set_active_track_index is usually only useful in scenarios where we want to reinstate
# a previous active track after switching to a different track (without knowing what that
# previous track was). For everything else we should use #set.

# Store the active track index and enable the color track to carry out work on it.
tid: int = zbc.get_active_track_index()
if not zbc.set("Movie:Timeline Tracks:Color", True):
    raise RuntimeError("Failed to enable color track.")

# ...

# And now revert back to the old track, whatever it was.
if not zbc.set_active_track_index(tid):
    raise RuntimeError("Failed to restore previous active track.")