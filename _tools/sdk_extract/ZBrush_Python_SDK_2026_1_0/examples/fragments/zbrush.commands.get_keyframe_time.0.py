"""Code fragment for zbrush.commands.get_keyframe_time.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the total length of the document in seconds.
max_time: float = zbc.get("Movie:TimeLine:Duration")

# Get the time value for the second keyframe in the current track. It will return the value
# nrm_time in the interval [0, 1] and we then convert this to a value in seconds.

i: int = 1 # The second keyframe, the first one would be 0.
nrm_time: float = zbc.get_keyframe_time(i)
if nrm_time < 0:
    raise ValueError(f"No keyframe found at the given index: {i}")

sec_time: float = nrm_time * max_time
print(f"The keyframe at index {i} is at {round(sec_time, 2)} seconds ({round(nrm_time, 2)}%).")
