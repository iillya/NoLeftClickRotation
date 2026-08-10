"""Code fragment for zbrush.commands.add_note_button.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# The IDs of the buttons we are going to add to our note. ZBrush assigns implicitly IDs starting with 
# 1 in the order the buttons are added.
ID_BTN_COLOR: int = 2
ID_BTN_CLOSE: int = 3

def run_note(title: str) -> str:
    '''Runs a simple note interface and returns a message when the user made a choice.
    '''
    # Notes are a bit weird in that they do not really have numeric inputs apart from switches. The
    # common workflow is to use buttons and then either use them as checks which switch out their
    # text for the empty string or an "x" or to cycle through a set of strings to emulate a value 
    # range.

    # The states of a dropdown/cycle we want to emulate.
    states: list[str] = ["Red", "Green", "Blue"]
    # The currently selected state.
    current_state: int = states[0]

    # Now comes the big trick, notes are often implemented in a loop to emulate interactivity, 
    # because out of the box, note controls do not have callback functions. So, we build a note,
    # poll its output, loop around, and build it again with the new state.
    while True:
        # Add three buttons to the note which is opened next. The first button is just a label
        # emulated by a disabled button. The second button shows the current state and the third 
        # button is a close button.
        zbc.add_note_button(name="Color:", initially_disabled=True, bg_opacity=0) # ID: 1
        zbc.add_note_button(name=str(current_state))                              # ID: 2
        zbc.add_note_button(name="Close")                                         # ID: 3

        # Now show the note which will return the ID of the first control clicked by the user, i.e.,
        # the next line runs from the note being opened until the user clicks something.
        result: int = zbc.show_note(title)

        # Bases on the clicked element, we either cycle the state or close the dialog. When we close
        # the dialog, we return the current state and with that exit the loop. Otherwise, we loop
        # around, rebuild the dialog with the new state, and show it again. Inputs smaller than one
        # are keyboard events like ESC or Enter, we also treat them as close events.
        if result == ID_BTN_COLOR:
            current_index: int = states.index(current_state)
            next_index: int = (current_index + 1) % len(states)
            current_state = states[next_index]
        elif result == ID_BTN_CLOSE or result <= 0: 
            return current_state

if __name__ == "__main__":
    result: str = run_note("Hello World!")
    zbc.message_ok(f"The chosen color is: {result}")
