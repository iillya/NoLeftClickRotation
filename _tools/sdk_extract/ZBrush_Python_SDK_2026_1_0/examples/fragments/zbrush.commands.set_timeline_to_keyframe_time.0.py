"""Code fragment for zbrush.commands.set_timeline_to_keyframe_time.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the total length of the document in seconds and the total count of keyframes in the current track.
max_time: float = zbc.get("Movie:TimeLine:Duration")
count: int = zbc.get_keyframes_count()
if count < 1:
    raise RuntimeError("Cannot set current time to keyframe of an empty track.")

# Set the current time to the last keyframe in the current track and print the absolute time in seconds.
i: int = count - 1
t_doc: float = zbc.set_timeline_to_keyframe_time(i)
t_sec: float = t_doc * max_time

print(f"Set current time to keyframe {i} at {round(t_sec, 2)} seconds.")
