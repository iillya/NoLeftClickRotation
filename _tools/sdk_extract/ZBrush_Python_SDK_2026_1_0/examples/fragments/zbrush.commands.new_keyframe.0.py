"""Code fragment for zbrush.commands.new_keyframe.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the total length of the document in seconds.
max_time: float = zbc.get("Movie:TimeLine:Duration")

# Create a keyframe at five seconds.
if max_time < 5:
    raise RuntimeError("Cannot create keyframe at 5 seconds for a document shorter than 5 seconds.")

t_sec: float = 5.0
t_doc: float = t_sec / max_time
kid: int = zbc.new_keyframe(t_doc)
if kid == -1:
    raise RuntimeError("Failed to create keyframe.")

print(f"Created keyframe with index {kid} at {round(t_sec, 2)} seconds.")

# We can of course also make use of the relative time format Zbrush uses and create keyframes at
# 25%, 50%, and 75% of the document length, but that is probably only rarely useful.
ids: list[int] = [
    zbc.new_keyframe(0.25),
    zbc.new_keyframe(0.50),
    zbc.new_keyframe(0.75),
]
if -1 in ids:
    raise RuntimeError("Failed to create keyframes.")

print(f"Created keyframes with indices {ids} at 25%, 50%, and 75% of the document length.")

# And just to state the obvious here: Creating new keyframes can invalidate existing keyframe 
# indices. #kid could now be an invalid index, unless max_time * 0.25 was a value greater than 
# five seconds (and the new keyframes in #ids therefore would all lie after #kid).
