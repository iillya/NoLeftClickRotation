"""Demonstrates how to add and delete keyframes in the timeline of ZBrush.

ZBrush divides its timeline into purpose bound tracks such as camera, color, material, or tool
animations. This script creates ten color keyframes in the color track of the document. The script
also explains the normalized time format ZBrush is using.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "21/08/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def main() -> None:
    """Executed when ZBrush runs this script.
    """
    # Make sure the timeline is unfolded.
    if not zbc.get("Movie:TimeLine:Show"):
        zbc.set("Movie:TimeLine:Show", True)

    # Activate track edit mode, activate the color track, and delete all existing keyframes in it.
    zbc.set("Movie:TimeLine Tracks:Edit", True)
    zbc.set("Movie:TimeLine Tracks:Color", True)
    count: int = zbc.get_keyframes_count()
    if count > 0:
        print(f"Deleting {count} color keyframes.")
        for i in range(count):
            zbc.delete_keyframe(i)

    # Now we get the length of the timeline because ZBrush makes the a bit odd choice to specify
    # all time values in its API as document normalized values. So, for example, when we have a 
    # document which is 10 seconds long, and we want to create a keyframe at 5 seconds, we have to 
    # pass 0.5 as the normalized time value (because 5 / 10 = 0.5).
    max_time: float = zbc.get("Movie:TimeLine:Duration")
    if (max_time < 10.0):
        zbc.show_note("Cannot create keyframes in a timeline shorter than 10 seconds.", 
                      display_duration=2.0)
        
    # Define ten colors for ten color key frames to generate.
    color_list: list[tuple[int, int, int]] = [
        (255, 0, 0), (125, 125, 0), (0, 255, 0), (0, 125, 125), (0, 0, 255), (125, 0, 125),
        (255, 0, 255), (255, 125, 0), (255, 255, 0), (0, 255, 255),
    ]

    # Create ten keyframes for the defined colors with a spacing of one second each.
    for i, color in enumerate(color_list):
        # Set the current color.
        zbc.set_color(*color)
        # Compute the normalized document time for #i seconds and then set a keyframe.
        time: float = i / max_time
        zbc.new_keyframe(time)

    print(f"Timeline has {zbc.get_keyframes_count()} color keyframes.")

if __name__ == "__main__":
    main()