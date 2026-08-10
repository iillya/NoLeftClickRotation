"""Provides an example for a very literal port of a ZScript script to Python.

This directory contains three examples for notes interfaces. All three implement the same
coffee maker interface, where the user can select a coffee type and then serve it. The examples are:

- ex_gui_notes.py            : A modern Pythonic implementation of a notes interface.
- ex_gui_zscript_port.py     : A literal port of a ZScript notes interface to Python.
- ex_gui_zscript_orginal.txt : The original ZScript notes example for reference.

It is recommended to use the ex_gui_notes.py example as a reference for building modern notes code,
and this example only as a reference for porting ZScript code to Python.
"""
__author__ = "Javier Edo"
__date__ = "21/08/2025"
__copyright__ = "Maxon Computer"

import os

import zbrush.commands as zbc

message = ""

def note_interface():
    hSize = 20
    vSize = 18
    vPos = 87
    hPos = 23
    space = 12
    choice = [True, False, False, False, False]
    choiceImage = [
        "images/expresso.jpg", 
        "images/cappuccino.jpg",
        "images/latte.jpg",
        "images/mocha.jpg",
        "images/flat white.jpg"]
    choiceText = ["X", "", "", "", ""]
    cupPic = choiceImage[0]

    global message

    while True:
        zbc.add_note_button("", "images/ZCoffeeBack.jpg", 0, 1, 1, 305, 320, 0, 0, 0, 1, 1)

        for x in range(5):
            zbc.add_note_button(
                choiceText[x], "", choice[x], False, hPos, vPos+((vSize+space)*x), hSize, vSize, 
                -1, 0xffa000, 1.0, 1.0, 1.0)

        zbc.add_note_button(
            "", cupPic, False, True, 149, 135, 0.0, 0.0, -1, -1, 1.0, 1.0, 1.0)
        zbc.add_note_button(
            "Cancel", "", False, False, 170, 260, 100, 25, -1, -1, 1.0, 1.0, 1.0)
        zbc.add_note_button(
            "Serve Now", "", False, False, 30, 260, 100, 25, -1, 0xffa000, 1.0, 1.0, 1.0)

        result = zbc.show_note("")

        if result >= 2 and result <= 6:
            if choice[result - 2]:
                choice[result - 2] = False
                choiceText[result - 2] = ""
                cupPic = "images/ZCoffeeEmpty.jpg"
                message = "\Cffa000\n  What, no coffee?!\n"
            else:
                for i in range(5):
                    if choice[i]:
                        choice[i] = False
                        choiceText[i] = ""
                choice[result - 2] = True
                choiceText[result - 2] = "X"
                cupPic = choiceImage[result - 2]

        elif result == 8: # Cancel button
            message = "\Cffa000\n  What, no coffee?!\n"
            return

        if result < 2 or result > 8: # Serve Now button or press Spacebar
            if (choice[0] == 0 and choice[1] == 0 and choice[2] == 0 and choice[3] == 0 and 
                choice[4] == 0):
                # all choices are unchecked, so no coffee selected
                zbc.show_note("\Cc0c0c0\n  Sorry, we do not serve empty cups.\n  Please make a "
                              "choice or press \Cffa000Cancel\Cc0c0c0.\n", "",3,4737096,0,320)
            else:
                message = os.path.splitext(os.path.basename(cupPic))[0]
                message = "\Cc0c0c0Enjoy your \Cffa000" + message + "\Cc0c0c0 !\n"
                return

def open_note():
    zbc.freeze(note_interface)
    zbc.show_note(message, "",2,4737096,0,220)

if __name__ == "__main__":
    open_note()
