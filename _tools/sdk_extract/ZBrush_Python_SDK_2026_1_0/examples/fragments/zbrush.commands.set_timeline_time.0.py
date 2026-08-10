"""Code fragment for zbrush.commands.set_timeline_time.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the total length of the document in seconds.
max_time: float = zbc.get("Movie:TimeLine:Duration")
if max_time < 5:
    raise RuntimeError("Cannot set current time to 5 seconds for a document shorter than 5 seconds.")

# Set the current time to five seconds.
t_doc: float = 5.0 / max_time
if not zbc.set_timeline_time(t_doc):
    raise RuntimeError("Failed to set current time.")
