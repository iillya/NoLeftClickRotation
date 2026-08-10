"""Code fragment for zbrush.commands.add_note_switch.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Add two switch buttons to the next note which is shown, one initially off and one initially on.
zbc.add_note_switch(name="Switch A", initially_pressed=False)
zbc.add_note_switch(name="Switch B", initially_pressed=True)
zbc.add_note_button(name="Close")
zbc.show_note("Note with Switch")

# Query the state of the two switches after the user has closed the note.
state_a: bool = zbc.get_from_note("Switch A")
state_b: bool = zbc.get_from_note("Switch B")
print(f"Switch A is {'ON' if state_a else 'OFF'}")
print(f"Switch B is {'ON' if state_b else 'OFF'}")