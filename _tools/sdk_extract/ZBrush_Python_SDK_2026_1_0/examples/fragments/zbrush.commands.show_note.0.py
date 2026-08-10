"""Code fragment for zbrush.commands.show_note.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def show_note_delayed(title: str) -> None:
    '''Display a note that will not open on its own but will be included with the next note which 
    is shown.
    '''
    zbc.add_note_button("Delayed Button")
    zbc.show_note(title, display_duration=-1)

def show_note(title: str) -> None:
    '''Display a note that will open immediately and close when the user clicks a button.
    '''
    zbc.add_note_button("Button")
    zbc.show_note(title, display_duration=0)

def show_note_timed(title: str, message: str, duration: float):
    '''Display a note that will open immediately and close after a specified duration.
    '''
    zbc.add_note_button(message, initially_disabled=True, bg_opacity=0)
    # Also customize the note background color and icon of the note.
    blue: int = zbc.rgb(0, 125, 255)
    path: str = r"D:\\git\\zbrush-sdk\\examples\\gui\\images\\cappuccino.jpg"
    zbc.show_note(title, bg_color=blue, icon_path=path, display_duration=duration)

# First show two delayed notes and then a normal note (i.e., three notes at once) and after the user
# closes the normal note, show a timed note that will close automatically after 3 seconds.
show_note_delayed("Delayed Note")
show_note_delayed("Another Delayed Note")
show_note("User Terminated Note")
show_note_timed("Timed Note", "This note will close in 3 seconds", 3.0)
