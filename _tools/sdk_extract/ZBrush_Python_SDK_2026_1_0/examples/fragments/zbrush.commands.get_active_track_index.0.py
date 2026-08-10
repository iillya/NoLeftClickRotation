"""Code fragment for zbrush.commands.get_active_track_index.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the index of the currently enabled track. This information is usually only useful when
# we temporarily switch to another track and want to switch back later. 
tid: int = zbc.get_active_track_index()

# When we just want to know if a certain track is enabled, we must use #get and its item path.
material_track_is_enabled: bool = bool(zbc.get("Movie:Timeline Tracks:Material"))

print(f"Active track index: {tid}, material track enabled: {material_track_is_enabled}")