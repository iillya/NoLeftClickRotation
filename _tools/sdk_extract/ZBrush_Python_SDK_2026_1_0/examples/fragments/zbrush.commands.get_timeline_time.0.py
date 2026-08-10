"""Code fragment for zbrush.commands.get_timeline_time.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the total length of the document in seconds.
max_time: float = zbc.get("Movie:TimeLine:Duration")

# Get the current time, i.e., the position of the playhead in the timeline. This returns a
# normalized document time value in the interval [0, 1] which we then convert to a value in
# seconds.
t_doc: float = zbc.get_timeline_time()
t_sec: float = t_doc * max_time

print(f"The document playhead is at {round(t_sec, 2)} seconds ({round(t_doc, 2)}%).")