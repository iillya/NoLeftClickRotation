from typing import Any, Callable

class IPaletteDockingBar:
    ...


class ISubPaletteTitleMode:
    ...


class Stroke:
    """Represents a brush stroke in ZBrush.
    """

    def __init__(self, string: str) -> None:
        """Initializes a stroke from its string representation.

        Args:
            string (`str`): The string representation to initialize the stroke from.

        Example:
            .. literalinclude:: /../../examples/fragments/zbrush.commands.stroke.__init__.0.py
                :language: python
                :lines: 7-

        """
        ...

    def __repr__(self) -> str:
        """Returns the string representation of the stroke.

        Returns:
            str: The string representation of the stroke.
        """
        ...


class Strokes:
    """Represents a collection of brush strokes in ZBrush.

    """

    def __init__(self, string: str) -> None:
        """Initializes a collection of strokes from its string representation.

        Args:
            string (`str`): The string representation to initialize the stroke from.
        """
        ...

    def __repr__(self) -> str:
        """Returns the string representation of the collection of strokes.

        Returns:
            str: The string representation of the collection of strokes.
        """
        ...


__doc__: str
__name__: str


def add_button(item_path: str, info: str = '', fn: Callable = None, initially_disabled: bool = False, width: float = 0.0, hotkey: str = '', icon_path: str = '', height: float = 0.0) -> bool:
    """Adds a clickable button to a palette or sub-palette.

    Args:
        item_path (`str`): The item path for the button, whose last element will become the button's text.
        info (`str`, optional): The bubble help of the button. Defaults to the empty string.
        fn (`Callable`, optional): The callback which is invoked when the button is pressed. Must follow the signature `f(sender: str) -> None`.
        initially_disabled (`bool`, optional): If the button should be initially not clickable. Defaults to `False`.
        width (`float`, optional): The width of the button in pixels. Setting the width to `0` will make it auto-width, positive values will set a specific width for the button. Defaults to `0`.
        hotkey (`str`, optional): An optional hotkey for the button. If specified, the button can be activated by pressing the hotkey.

            .. include:: /partials/api_shortcuts.rst

        icon_path (`str`, optional): The path to an optional icon for the button. The icon should be a `BMP` or `PSD` file.
        height (`float`, optional): The height of the button in pixels. Setting the height to `0` will make it auto-height, positive values will set a specific height for the button. Defaults to `0`.

    Returns:
        bool: `True` if the button was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_button.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_curve_point(curve_index: int, x: float, y: float, z: float) -> int:
    """Adds a new point to the specified curve.

    Args:
        curve_index (`int`): The zero-based index of the curve to which the point should be added.
        x (`float`): x position
        y (`float`): y position
        z (`float`): z position

    Returns:
        int: The zero indexed index of the added point, or `-1` if the operation failed.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_curve_point.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_new_curve() -> int:
    """Adds a new curve to the current curves list.

    Returns:
        int: The zero-based index of the newly created curve, or `-1` if the operation failed.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_new_curve.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_note_button(name: str, icon_path: str = '', initially_pressed: bool = False, initially_disabled: bool = False, h_rel_position: float = 0.0, v_rel_position: float = 0.0, width: float = 0.0, height: float = 0.0, bg_color: int = -1, text_color: int = -1, bg_opacity: float = 1.0, text_opacity: float = 1.0, img_opacity: float = 1.0) -> bool:
    """Adds a clickable button to the next note dialog which is shown.

    Args:
        name (`str`): The string item path and text for the button.
        icon_path (`str`, optional): The path to an icon for the button. Must be a `BMP` or `PSD` file. Defaults to an empty string (no icon).
        initially_pressed (`bool`, optional): Specifies if the button is initially pressed. Default to `False`.
        initially_disabled (`bool`, optional): Specifies if the button is initially not clickable. Default to `False`.
        h_rel_position (`float`, optional): The horizontal relative position of the button. `0` means automatic positioning, positive values offset from the left, and negative values offset from the right. Defaults to `0.0`.
        v_rel_position (`float`, optional): The vertical relative position of the button. `0` means automatic positioning, positive values offset from the top, and negative values offset from the bottom. Defaults to `0.0`.
        width (`float`, optional): The width of the button in pixels. Setting the width to `0` will make it auto-width, positive values will set a specific width for the button. Defaults to `0.0`.
        height (`float`, optional): The height of the button in pixels. Setting the height to `0` will make it auto-height, positive values will set a specific height for the button. Defaults to `0.0`.
        bg_color (`int`, optional): The background color of the button, computed with the formula `(blue + (green * 256) + (red * 65536))`. Defaults to `-1` (no color).
        text_color (`int`, optional): The text color of the button, computed with the formula `(blue + (green * 256) + (red * 65536))`. Defaults to `-1` (no color).
        bg_opacity (`float`, optional): The background opacity of the button. Defaults to `1.0`.
        text_opacity (`float`, optional): The text opacity of the button. Defaults to `1.0`.
        img_opacity (`float`, optional): The image opacity of the button. Defaults to `1.0`.

    Returns:
        bool: `True` if the button was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_note_button.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_note_switch(name: str, icon_path: str = '', initially_pressed: bool = False, initially_disabled: bool = False, h_rel_position: float = 0.0, v_rel_position: float = 0.0, width: float = 0.0, height: float = 0.0, bg_color: int = -1, text_color: int = -1, bg_opacity: float = 1.0, text_opacity: float = 1.0, img_opacity: float = 1.0) -> bool:
    """Adds a switch button to the next note dialog which is shown.

    Args:
        name (`str`): The string item path and text for the switch.
        icon_path (`str`, optional): The path to an icon for the switch button. Must be a `BMP` or `PSD` file. Defaults to an empty string (no icon).
        initially_pressed (`bool`, optional): Specifies if the switch button is initially pressed. Defaults to `False`.
        initially_disabled (`bool`, optional): Specifies if the switch button is initially not clickable. Defaults to `False`.
        h_rel_position (`float`, optional): The horizontal relative position of the button. `0` means automatic positioning, positive values offset from the left, and negative values offset from the right. Defaults to `0.0`. 
        v_rel_position (`float`, optional): The vertical relative position of the button. `0` means automatic positioning, positive values offset from the top, and negative values offset from the bottom. Defaults to `0.0`.
        width (`float`, optional): The width of the button in pixels. Setting the width to `0` will make it auto-width, positive values will set a specific width for the button. Defaults to `0.0`.
        height (`float`, optional): The height of the button in pixels. Setting the height to `0` will make it auto-height, positive values will set a specific height for the button. Defaults to `0.0`.
        bg_color (`int`, optional): The background color of the button, computed with the formula `(blue + (green * 256) + (red * 65536))`. Defaults to `-1` (no color).
        text_color (`int`, optional): The text color of the button, computed with the formula `(blue + (green * 256) + (red * 65536))`. Defaults to `-1` (no color).
        bg_opacity (`float`, optional): The background opacity of the button. Defaults to `1.0`.
        text_opacity (`float`, optional): The text opacity of the button. Defaults to `1.0`.
        img_opacity (`float`, optional): The image opacity of the button. Defaults to `1.0`.

    Returns:
        bool: `True` if the switch button was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_note_switch.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_palette(item_path: str, docking_bar: int, shortcut: str = '') -> bool:
    """Adds a new palette to the menu.

    .. note::

        A palette is a top-level menu in ZBrush, and it can contain sub-palettes, buttons, sliders, and switches. To add an area in an existing palette, use :func:`add_subpalette<zbrush.commands.add_subpalette>` instead.

    Args:
        item_path (`str`): The item path for the palette, whose last element will become the palette's name.
        docking_bar (`int`, optional): Specifies the docking behavior. `0` means the palette will be docked in the left menu bar, `1` means it will be docked in the right menu bar. Defaults to `0`.
        shortcut (`str`, optional): An optional shortcut for the palette. If specified, the palette can be opened by pressing the shortcut key. Defaults to an empty string (no shortcut).

    Returns:
        bool: `True` if the palette was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_palette.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_slider(item_path: str, cur_value: float, resolution: int, min_value: float, max_value: float, info: str = '', fn: Callable = None, initially_disabled: bool = False, width: float = 0.0, height: float = 0.0) -> bool:
    """Adds a draggable slider to a palette or sub-palette.

    A slider is a gadget that allows the user to select a value from a range by dragging a handle along a track. 

    Args:
        item_path (`str`): The item path for the slider, whose last element will become the slider's name.
        cur_value (`float`): The initial value of the slider.
        resolution (`int`): The step size of the slider. When the slider has a range of `[0, 10]` for example, and you set the resolution to `2`, the slider will snap to the values `0, 2, 4, 6, 8, 10`. Setting the resolution to `0` means the slider will not snap to ticks.
        min_value (`float`): The minimum value of the slider.
        max_value (`float`): The maximum value of the slider.
        info (`str`, optional): The bubble help of the slider. Defaults to an empty string.
        fn (`Callable`, optional): The callback of the slider which is invoked when the slider's value changes. Must conform to the signature `f(sender: str, value: float) -> None`, where `sender` is the slider's item path and `value` is the current value of the slider. The callback of a slider is only called at the end of a drag operation and not during it.
        initially_disabled (`bool`, optional): Specifies if the slider is initially disabled. Defaults to `False`.
        width (`float`, optional): The width of the slider in pixels. Setting the width to `0` will make it auto-width, positive values will set a specific width for the button. Defaults to `0.0`.
        height (`float`, optional): The height of the slider in pixels. Setting the height to `0` will make it auto-height, positive values will set a specific height for the button. Defaults to `0.0`.

    Returns:
        bool: `True` if the slider was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_slider.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_subpalette(item_path: str, title_mode: int, icon_path: str = '', left_inset: float = 0.0, right_inset: float = 0.0, top_inset: float = 0.0, bottom_inset: float = 0.0) -> bool:
    """Adds a sub-palette to a palette or another sub-palette.

    .. note::

        Insets will require manually sized elements or will result in auto-sized elements being cut off.

    Args:
        item_path (`str`): The item path for the sub-palette, whose last element will become the sub-palette's name.
        title_mode (`int`, optional): The title bar style of the sub-palette. `0` will show the title and minimize button, `1` will show the title without the minimize button, and `2` will hide the title bar completely. Defaults to `0`.
        icon_path (`str`, optional): The path to an optional gray-scale (8-bits) icon for the sub-palette. The icon should be a `BMP` or `PSD` file and have the standard size of 20 pixels squared. Defaults to the empty string (no icon).
        left_inset (`float`, optional): The left margin of elements in the sub-palette to its border. `0` means no inset, positive values will add an inset from the left, and negative values will add an inset from the right. Defaults to `0.0`.
        right_inset (`float`, optional): The right margin of elements in the sub-palette to its border. `0` means no inset, positive values will add an inset from the right, and negative values will add an inset from the left. Defaults to `0.0`.
        top_inset (`float`, optional): The top margin of elements in the sub-palette to its border. `0` means no inset, positive values will add an inset from the top, and negative values will add an inset from the bottom. Defaults to `0.0`.
        bottom_inset (`float`, optional): The bottom margin of elements in the sub-palette to its border. `0` means no inset, positive values will add an inset from the bottom, and negative values will add an inset from the top. Defaults to `0.0`.

    Returns:
        bool: `True` if the sub-palette was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_subpalette.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_switch(item_path: str, initial_state: bool, info: str = '', fn: Callable = None, initially_disabled: bool = False, width: float = 0.0, height: float = 0.0, icon_path: str = '') -> bool:
    """Adds a switch to a palette or sub-palette.

    A switch is a gadget that allows the user to toggle a state on or off. 

    Args:
        item_path (`str`): The item path for the switch, whose last element will become the switch's name.
        initial_state (`bool`): The initial state of the switch. `True` means the switch is on, `False` means it is off. Defaults to `False`.
        info (`str`, optional): The bubble help of the switch. Defaults to an empty string.
        fn (`Callable`, optional): The callback function which is invoked when the switch's state changes. Must conform to the signature `fn(sender: str, value: bool) -> None`, where `sender` is the switch's item path and `value` is the current state of the switch.
        initially_disabled (`bool`, optional): Specifies if the switch is initially disabled. Defaults to `False`.
        width (`float`, optional): The width of the switch in pixels. Setting the width to `0` will make it auto-width, positive values will set a specific width for the button. Defaults to `0.0`.
        height (`float`, optional): The height of the switch in pixels. Setting the height to `0` will make it auto-height, positive values will set a specific height for the button. Defaults to `0.0`.
        icon_path (`str`, optional): The path to an optional icon for the switch. The icon should be a `BMP` or `PSD` file. Defaults to an empty string (no icon).

    Returns:
        bool: `True` if the switch was successfully added, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_switch.0.py
            :language: python
            :lines: 7-

    """
    ...


def add_zsphere(x: float, y: float, z: float, radius: float, parent_index: int, color: int = -1, mask: int = 0, time_stamp: int = 0, flags: int = 0) -> int:
    """Adds a new ZSphere to the currently active ZSpheres tool.

    .. warning::

        Editing ZSphere operations always must happen in the context of a :func:`edit_zsphere <zbrush.commands.edit_zsphere>` call.

    Args:
        x (`float`): The x position of the new ZSphere.
        y (`float`): The y position of the new ZSphere.
        z (`float`): The z position of the new ZSphere.
        radius (`float`): The radius of the new ZSphere.
        parent_index (`int`): The zero based index index of the parent ZSphere.
        color (`int`, optional): The color of the new ZSphere, computed with the formula `(blue + (green * 256) + (red * 65536))`. Defaults to `-1` (no color).
        mask (`int`, optional): The mask value of the new ZSphere from `0` to `255`. `0` means unmasked, `255` means fully masked. Defaults to `0`.
        time_stamp (`int`, optional): The time stamp of the new ZSphere. Defaults to `0`.
        flags (`int`, optional): The flags for the new ZSphere. `0` means default flags, `1` means invisible link to parent. Defaults to `0`.

    Returns:
        int: The zero indexed index of the newly created ZSphere, or `-1` if the operation failed.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.add_zsphere.0.py
            :language: python
            :lines: 7-

    """
    ...


def ask_filename(extensions: str, default_file_name: str = '', title: str = '') -> str:
    """Opens a file loading or saving dialog and returns the selected file name.

    The function does not carry out the actual loading or saving of the file, it only provides a dialog for the user to 
    select a file name. The actual file operations must be handled separately.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Args:
        extensions (`str`): A string containing the file extensions and their descriptions. Up to three extensions can be specified, following the format `"Label A (*.ext1)|*.ext1|Label B (*.ext2)|*.ext2|Label A C (*.ext3)|*.ext3"`. 
        default_file_name (`str`, optional): Default fileName for `SaveDialog`, will open `OpenDialog` if empty.
        title (`str`, optional): The title of the file dialog. Defaults to an empty string.

    Returns:
        str: The full path of the selected file, or an empty string if the dialog was canceled.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.ask_filename.0.py
            :language: python
            :lines: 7-

    """
    ...


def ask_string(initial_string: str = '', title: str = '') -> str:
    """Displays a text input dialog and returns the string typed by user.

    Args:
        initial_string (`str`, optional): The initial string to display in the input dialog. Defaults to an empty string.
        title (`str`, optional): The title of the input dialog. Defaults to an empty string.

    Returns:
        str: The string entered by the user, or an empty string if the dialog was canceled

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.ask_string.0.py
            :language: python
            :lines: 7-

    """
    ...


def canvas_click(X1: float, Y1: float, X2: float | None = None, Y2: float | None = None, X3: float | None = None, Y3: float | None = None, X4: float | None = None, Y4: float | None = None, X5: float | None = None, Y5: float | None = None, X6: float | None = None, Y6: float | None = None, X7: float | None = None, Y7: float | None = None, X8: float | None = None, Y8: float | None = None) -> None:
    """Emulates a click within the canvas area.

    Args:
        X1 (`float`): The X coordinate of the click position.
        Y1 (`float`): The Y coordinate of the click position.
        X2 (`float`, optional): The X coordinate of the first drag position.
        Y2 (`float`, optional): The Y coordinate of the first drag position.
        X3 (`float`, optional): The X coordinate of the second drag position.
        Y3 (`float`, optional): The Y coordinate of the second drag position.
        X4 (`float`, optional): The X coordinate of the third drag position.
        Y4 (`float`, optional): The Y coordinate of the third drag position.
        X5 (`float`, optional): The X coordinate of the fourth drag position.
        Y5 (`float`, optional): The Y coordinate of the fourth drag position.
        X6 (`float`, optional): The X coordinate of the fifth drag position.
        Y6 (`float`, optional): The Y coordinate of the fifth drag position.
        X7 (`float`, optional): The X coordinate of the sixth drag position.
        Y7 (`float`, optional): The Y coordinate of the sixth drag position.
        X8 (`float`, optional): The X coordinate of the seventh drag position.
        Y8 (`float`, optional): The Y coordinate of the seventh drag position.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.canvas_click.0.py
            :language: python
            :lines: 7-

    """
    ...


def canvas_stroke(stroke: Stroke, delayed: bool | None = None, rotation: float | None = None, h_scale: float | None = None, v_scale: float | None = None, h_offset: float | None = None, v_offset: float | None = None) -> bool:
    """Applies a brush stroke within the current canvas area.

    .. note::

        The origin for all stroke transformations is the start of the stroke and they are carried out in canvas space.

    Args:
        stroke (:class:`Stroke`): The stroke object to apply.
        delayed (`bool`, optional): If to delay updates of the canvas until the end of the strokes. Defaults to `None`.
        rotation (`float`, optional): A rotation to apply to the stroke data. Defaults to `None`.
        h_scale (`float`, optional): A horizontal scale to apply to the stroke data. Defaults to `None`.
        v_scale (`float`, optional): A vertical scale to apply to the stroke data. Defaults to `None`.
        h_offset (`float`, optional): A horizontal offset to apply to the stroke data. Defaults to `None`.
        v_offset (`float`, optional): A vertical offset to apply to the stroke data. Defaults to `None`.
        h_rot_center (`float`, optional): A horizontal rotation center to apply to the stroke data. Defaults to `None`.
        v_rot_center (`float`, optional): A vertical rotation center to apply to the stroke data. Defaults to `None`.

    Returns:
        bool: `True` if the stroke was successfully applied, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.canvas_stroke.0.py
            :language: python
            :lines: 7-

    """
    ...


def canvas_strokes(strokes: Strokes, delayed: bool | None = None, rotation: float | None = None, h_scale: float | None = None, v_scale: float | None = None, h_offset: float | None = None, v_offset: float | None = None, h_rot_center: float | None = None, v_rot_center: float | None = None) -> bool:
    """Applies multiple brush strokes within the current canvas area.

    Args:
        strokes (:class:`Strokes`): The stroke collection object to apply.
        delayed (`bool`, optional): If to delay updates of the canvas until the end of the strokes. Defaults to `None`.
        rotation (`float`, optional): A rotation to apply to the stroke data. Defaults to `None`.
        h_scale (`float`, optional): A horizontal scale to apply to the stroke data. Defaults to `None`.
        v_scale (`float`, optional): A vertical scale to apply to the stroke data. Defaults to `None`.
        h_offset (`float`, optional): A horizontal offset to apply to the stroke data. Defaults to `None`.
        v_offset (`float`, optional): A vertical offset to apply to the stroke data. Defaults to `None`.
        h_rot_center (`float`, optional): A horizontal rotation center to apply to the stroke data. Defaults to `None`.
        v_rot_center (`float`, optional): A vertical rotation center to apply to the stroke data. Defaults to `None`.

    Returns:
        bool: `True` if the strokes were successfully applied, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.canvas_strokes.0.py
            :language: python
            :lines: 7-

    """
    ...


def click(item_path: str, X1: float | None = None, Y1: float | None = None, X2: float | None = None, Y2: float | None = None, X3: float | None = None, Y3: float | None = None, X4: float | None = None, Y4: float | None = None, X5: float | None = None, Y5: float | None = None, X6: float | None = None, Y6: float | None = None, X7: float | None = None, Y7: float | None = None) -> None:
    """Clicks the interface item at the given path.

    Args:
        item_path (`str`): The interface path of the item to click.
        X1 (`float`, optional): The X coordinate of the click position.
        Y1 (`float`, optional): The Y coordinate of the click position.
        X2 (`float`, optional): The X coordinate of the first drag position.
        Y2 (`float`, optional): The Y coordinate of the first drag position.
        X3 (`float`, optional): The X coordinate of the second drag position.
        Y3 (`float`, optional): The Y coordinate of the second drag position.
        X4 (`float`, optional): The X coordinate of the third drag position.
        Y4 (`float`, optional): The Y coordinate of the third drag position.
        X5 (`float`, optional): The X coordinate of the fourth drag position.
        Y5 (`float`, optional): The Y coordinate of the fourth drag position.
        X6 (`float`, optional): The X coordinate of the fifth drag position.
        Y6 (`float`, optional): The Y coordinate of the fifth drag position.
        X7 (`float`, optional): The X coordinate of the sixth drag position.
        Y7 (`float`, optional): The Y coordinate of the sixth drag position.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.click.0.py
            :language: python
            :lines: 7-

    """
    ...


def close(item_path: str, show_zoom_rects: bool = False, parent_window: bool = False) -> None:
    """Closes a palette or sub-palette.

    Args:
        item_path (`str`): The interface path of the item to close.
        show_zoom_rects (`bool`, optional): If to show the zoom rectangle. Defaults to `False`.
        parent_window (`bool`, optional): If to target the parent of the specified item instead. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.close.0.py
            :language: python
            :lines: 7-

    """
    ...


def config(version: float) -> None:
    """Sets ZBrush to the configuration associated with the given `version`.

    This function can be useful to ensure a starting point for a script. Because the *series of button clicks* style scripts which are popular in the ZBrush API can rely on a specific application state to properly work. For more defensive code which ensures itself that certain items exist and are set to the required value, calling this function is not necessary.

    It is up to you to decide what to do: Either call this function and with that possibly overwrite user settings at the advantage of less verbose and defensive code. Or write more verbose, defensive, and with that longer code at the advantage of not having to overwrite the configuration of the user.

    Args:
        version (`float`): The version of ZBrush this instance should mimic in its settings. This only works in a downwards fashion for obvious reasons. E.g., a 2026 version of ZBrush can mimic a 2025 version, but a 2025 version cannot mimic a 2026 version.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.config.0.py
            :language: python
            :lines: 7-

    """
    ...


def create_displacement_map(width: int, height: int, smooth: bool = True, sub_poly: int = 0, border: int = 8, uv_tile: int = 1000000, use_hd: bool = True) -> None:
    """Creates a displacement map for the currently active tool.

    The tool must have a UV map for the displacement map, and be set to the 0th sub-division level for this command to work properly.

    Args:
        width (`int`): The width of the displacement map image.
        height (`int`): The height of the displacement map image.
        smooth (`bool`, optional): If to smooth the displacement map. Defaults to `True`.
        sub_poly (`int`, optional): The sub-poly level to use for the displacement map. Defaults to `0`.
        border (`int`, optional): The border size in pixels for the displacement map. Defaults to `8`.
        uv_tile (`int`, optional): The UV tile index to use for the displacement map. If set to `1000000`, it ignores UV tiles. Defaults to `1000000`.
        use_hd (`bool`, optional): If to use HD for the displacement map. Defaults to `True`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.create_displacement_map.0.py
            :language: python
            :lines: 7-

    """
    ...


def create_mesh_from_curves(name: str, action: int = 0, thickness: float = 0.0) -> int:
    """Creates a mesh from the current curves.

    Args:
        name (`str`): The name of the new mesh.
        action (`int`, optional): The action to perform. Defaults to `0`.

            ===== ===========================================
            `0`   Append mesh to the active mesh (default).
            `1`   Add as a new sub-tool.
            `2`   Export OBJ file if it does not exist.
            `3`   Export OBJ file and overwrite if it exists.
            ===== ===========================================
        thickness (`float`, optional): Thickness (zero = single side mesh)

    Returns:
        int: Number of points in the new mesh. `0` if the operation failed and `-1` if the file already exists.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.create_mesh_from_curves.0.py
            :language: python
            :lines: 7-

    """
    ...


def create_normal_map(width: int, height: int, smooth: bool = True, sub_poly: int = 0, border: int = 8, uv_tile: int = 1000000, local_coordinates: bool = False) -> None:
    """Creates a normal map for the currently active tool.

    Args:
        width (`int`): The width of the normal map image.
        height (`int`): The height of the normal map image.
        smooth (`bool`, optional): If to smooth the normal map. Defaults to `True`.
        sub_poly (`int`, optional): The sub-poly level to use for the normal map. Defaults to `0`.
        border (`int`, optional): The border size in pixels for the normal map. Defaults to `8`.
        uv_tile (`int`, optional): The UV tile index to use for the normal map. If set to `1000000`, it ignores UV tiles. Defaults to `1000000`.
        local_coordinates (`bool`, optional): Use tangent coordinates when set to `True`. If set to `False`, it uses world coordinates. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.create_normal_map.0.py
            :language: python
            :lines: 7-

    """
    ...


def curves_to_ui() -> int:
    """Copies the current list of curves to the active brush.

    .. warning::

        Calling this function is necessary to update the active brush with the current curves. Without it, changes will not be applied.

    Returns:
        int: `0` on success or `-1` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.curves_to_ui.0.py
            :language: python
            :lines: 7-

    """
    ...


def delete_curves() -> None:
    """Deletes the current curves list.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.delete_curves.0.py
            :language: python
            :lines: 7-

    """
    ...


def delete_interface_item(item_path: str) -> bool:
    """Deletes an interface item that has been added by a script.

    - Can only be used for script-generated interface items and can only be applied to gadgets. 
    - Does not work for palettes or sub-palettes, use :func:`close<zbrush.commands.close>` for these.

    Args:
        item_path (`str`): The path of item to delete.

    Returns:
        bool: `True` if the item was deleted successfully, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.delete_interface_item.0.py
            :language: python
            :lines: 7-

    """
    ...


def delete_keyframe(frame_index: int) -> int:
    """Deletes the keyframe at the given frame index in the timeline of ZBrush.

    Args:
        frame_index (`int`): The zero-based index of the keyframe to delete. This is not the index into all frames in the timeline but rather an index into the list of created keyframes. E.g., a document could have have 90 frames in total and keyframes at frame 0, 15, and 30. To get the second keyframe, we would pass `1` (a keyframe index) and not `15` (a frame index).

    Returns:
        int: The remaining number of keyframes on success or `-1` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.delete_keyframe.0.py
            :language: python
            :lines: 7-

    """
    ...


def delete_zsphere(index: int) -> int:
    """Deletes a ZSphere from the currently active ZSpheres tool.

    .. warning::

        Editing ZSphere operations always must happen in the context of a :func:`edit_zsphere <zbrush.commands.edit_zsphere>` call.

    .. warning::

        Deleting a ZSphere will not automatically delete its children but at the same time prevent you from manually deleting the children. So, you should always delete the children first.

    Args:
        index (`int`): The zero-based index of the ZSphere to delete. The root ZSphere (index 0) cannot be deleted.

    Returns:
        int: `0` on success or `-1` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.delete_zsphere.0.py
            :language: python
            :lines: 7-

    """
    ...


def disable(item_path: str) -> None:
    """Makes a script-generated interface item unresponsive to user interactions.

    .. include:: /partials/api_lock_disable.rst

    .. note::

        This function is the counterpart to :func:`enable<zbrush.commands.enable>` and both can be entirely replaced by :func:`set_status<zbrush.commands.set_status>`, see this latter function for code examples, as it is always the better choice.

    Args:
        item_path (`str`): The item path of the item to disable.

    """
    ...


def edit_zsphere(commands: Callable, store_undo: bool = False) -> None:
    """Makes the currently active ZSphere tool editable for API calls.

    Args:
        commands (`Callable`): The callable which carries out modifications to the active ZSphere tool.
        store_undo (`bool`, optional): If to create an undo point for the operations. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.edit_zsphere.0.py
            :language: python
            :lines: 7-

    """
    ...


def enable(item_path: str) -> None:
    """Makes a script-generated interface item responsive for user interactions.

    .. include:: /partials/api_lock_disable.rst

    .. note::

        This function is the counterpart to :func:`disable<zbrush.commands.disable>` and both can be entirely replaced by :func:`set_status<zbrush.commands.set_status>`, see this latter function for code examples, as it is always the better choice.

    Args:
        item_path (`str`): The item path of the item to enable.

    """
    ...


def exists(item_path: str) -> bool:
    """Verifies that the specified interface item exists.

    Args:
        item_path (`str`): The path of the item to check.

    Returns:
        bool: `True` if the item exists, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.exists.0.py
            :language: python
            :lines: 7-

    """
    ...


def fade_in(seconds: float = 0.5) -> None:
    """Not implemented.

    """
    ...


def fade_out(seconds: float = 0.5) -> None:
    """Not implemented.
    """
    ...


def freeze(fn: Callable, fade_time: float = 0.0) -> None:
    """Disables interface updates to avoid slowdowns while heavy operations are performed.

    .. note::

        Frozen will be most of the UI, but things like progress bars will still work. So, this is not entierly blocking, only in a sensible manner.

    Args:
        fn (`Callable`): The callable to execute which carries out the heavy operations which should not be slowed down.
        fade_time (`float`, optional): Fade in/out time in secs. Defaults to `0` secs.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.freeze.0.py
            :language: python
            :lines: 7-

    """
    ...


def get(item_path: str) -> float:
    """Returns the current numeric value of an interface item.

    .. note::

        See :func:`secondary<zbrush.commands.secondary>` for getting the secondary value of an item, e.g., the y-component of a 2D gadget.

    Args:
        item_path (`str`): The path of the item to get the value for.

    Returns:
        float: The current value of the item. All values (integers, booleans) are expressed as floats. Items such as buttons or sub-palettes which do not have any value will return `0.0`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_active_subtool_index() -> int:
    """Returns the index of the active sub-tool.

    The returned value reflects the position of a sub-tool in the list in 'Tool:Subtool'.

    Returns:
        int: The zero-based index of the active sub-tool. `-1` indicates an error.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_active_subtool_index.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_active_tool_index() -> int:
    """Returns the index of the active tool.

    Returns:
        int: The zero-based index of the active tool. `-1` indicates an error.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_active_tool_index.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_active_tool_path() -> str:
    """Returns the path of the active tool.

    For builtin tools this will be the name of the tool, e.g., "Sphere3D". For tools loaded from disk, it will be the full file path to the tool.

    Returns:
        str: The path of the active tool.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_active_tool_path.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_active_track_index() -> int:
    """Returns the index of the active track as selected in the 'Movie > Timeline Tracks' palette.

    Returns:
        int: The zero-based index of the active track. `-1` indicates an error.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_active_track_index.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_canvas_pan() -> tuple[float, float]:
    """Returns the offset of the for drawing used canvas area in relation to the visible canvas area on the screen.

    This function is only useful when a canvas zoom has been set via :func:`set_canvas_zoom<zbrush.commands.set_canvas_zoom>` and the canvas is therefore larger than the visible canvas area.

    .. warning::

        This does not return the camera offset, use :func:`get_transform<zbrush.commands.get_transform>` for that.

    Returns:
        tuple[float, float]: The X and Y offset of the canvas area used for drawing in relation to the visible canvas area on the screen.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_canvas_pan.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_canvas_zoom() -> float:
    """Returns the zoom of the for drawing used canvas area in relation to the visible canvas area on the screen.

    This function is only useful when a canvas zoom has been set via :func:`set_canvas_zoom<zbrush.commands.set_canvas_zoom>` and the canvas is therefore larger than the visible canvas area.

    .. warning::

        This does not return the camera zoom, use :func:`get_transform<zbrush.commands.get_transform>` for that.
    
    Returns:
        float: The zoom factor of the canvas area used for drawing in relation to the visible canvas area on the screen.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_canvas_zoom.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_flags(item_path: str) -> int:
    """[Private] Returns the status flags of the specified interface item.

    The status flags are a bitwise combination of other values already expressed by the API, such as an item being enabled/disabled, visible/invisible, or pressed. But they also include other information such as if an item is a button, slider, or toggle button. The only sensible public use is to check if two items have the same flags. 

    .. include:: /partials/api_flags.rst

    .. warning::

        The meaning of the individual item flag bits is intentionally not documented and may change without notice.

    Args:
        item_path (`str`): The item path of the item to get the flags for.

    Returns:
        int: The bitwise combination of the status flags of the item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_flags.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_from_note(index: int | str) -> Any:
    """Returns the value of a note gadget shown in the last displayed note.

    This mostly makes sense in the context of a :func:`add_note_switch<zbrush.commands.add_note_switch>` to retrieve the value of a switch.

    Args:
        index (`int` or `str`): The one-based index of name of the note gadget to get the value for.

    Returns:
        Any: The value of the note gadget.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_from_note.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_height(item_path: str) -> int:
    """Returns the height in pixels of the specified interface item.

    Args:
        item_path (`str`): The item path of the item to get the height for.

    Returns:
        int: Height in pixels of specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_height.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_hotkey(item_path: str) -> str:
    """Returns the shortcut of the specified interface item.

    .. include:: /partials/api_shortcuts.rst

    Args:
        item_path (`str`): Interface item path

    Returns:
        str: Shortcut of specified windowID interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_hotkey.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_id(item_path: str) -> int:
    """Returns the ID of the specified interface item.

    Functions which both accept an `int` or `str` for identifying an interface item, can take a value returned by this function as the `int` argument.

    Args:
        item_path (`str`): The interface item path to get the ID for.

    Returns:
        int: The id code of the specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_id.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_info(item_path: str) -> str:
    """Returns the bubble help text of the specified interface item.

    Args:
        item_path (`str`): The item path of the item to get the bubble help text for.

    Returns:
        str: The bubble help text of specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_info.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_keyframe_time(frame_index: int) -> float:
    """Gets the normalized document time for the keyframe at the given index in the active track.

    .. include:: /partials/api_zbrush_document_time.rst

    Args:
        frame_index (`int`): The zero-based index of the keyframe for which to get the normalized document time.

    Returns:
        float: The relative document time for the keyframe at the given index in the interval `[0, 1]` or `-1` if there is no keyframe at the given index in the active track.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_keyframe_time.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_keyframes_count() -> int:
    """Returns the total number of keyframes in the active track.

    Returns:
        int: The total number of keyframes in the active track.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_keyframes_count.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_last_stroke() -> Stroke:
    """Returns the stroke object for the last stroke that has been made.

    Returns:
        :class:`Stroke`: The latest stroke object.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_last_stroke.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_last_typed_filename() -> str:
    """Returns the file path for the last file name that was entered by a user in a load or save operation.

    As 'entering' counts both manually typing out a file and selecting it for example in a load dialog with a mouse click.

    .. note::

        Other than the function name implies, this function returns a full file path, and not just a file name.


    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Returns:
        str: The latest typed filename, can be the empty string when no filename has been yet typed.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_last_typed_filename.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_last_used_filename() -> str:
    """Returns the file path for the last file name that was entered by a user in a load or save operation.

    So, other than :func:`get_last_typed_filename`, this function does not require direct user input, just re-saving a file is enough to store its path. 

    .. note::

        Other than the function name implies, this function returns a full file path, and not just a file name.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Returns:
        str: The latest used filename, can be the empty string when no filename has been yet used.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_last_used_filename.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_left_mouse_button_state() -> bool:
    """Returns the current state of the left mouse button.

    Returns:
        bool: `True` if the left mouse button is currently pressed, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_left_mouse_button_state.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_max(item_path: str) -> float:
    """Returns the maximum possible numeric value the given interface item can take.

    Args:
        item_path (`str`): The item path of the item to get the maximum possible value for.

    Returns:
        float: The maximum possible value of the specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_max.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_min(item_path: str) -> float:
    """Returns the minimum possible numeric value the given interface item can take.

    Args:
        item_path (`str`): The item path of the item to get the minimum possible value for.

    Returns:
        float: The minimum possible value of the specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_min.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_mod(item_path: str) -> int:
    """Returns the current modifiers state of the given interface item.

    .. include:: /partials/api_modifiers.rst

    Args:
        item_path (`str`): The item path of the item to get the modifiers for.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_mod.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_mouse_pos(global_coordinates: bool = False) -> tuple[float, float]:
    """Returns the current mouse position in canvas or global world space coordinates.

    Args:
        global_coordinates (`bool`, optional): When set to `True`, the mouse position is returned in global window space. When set to `False`, the mouse position is returned in canvas space. Defaults to `False`.

    Returns:
        tuple[float, float]: The current mouse position as an (X, Y) tuple.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_mouse_pos.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_next_filename() -> str:
    """Returns the preset file path or file name used for the next load or save operation.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Returns:
        str: The file path or file name for the next operation. Can be the empty string when no file name preset. The outcome (path or name) depends on what has been set with :func:`set_next_filename` before.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_next_filename.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_next_template_filename() -> str:
    """Returns the template file path or file name used for the next load or save operation.

    Returns:
        str: The template file path or file name for the next operation. Can be the empty string when no template has been set.
    """
    ...


def get_polymesh3d_area() -> float:
    """Returns the area of current of the active sub-tool in the active tool.

    Returns:
        float: The area of the active sub-tool.
    """
    ...


def get_polymesh3d_volume() -> float:
    """Returns the volume of current of the active sub-tool in the active tool.

    Returns:
        float: The volume of the active sub-tool.
    """
    ...


def get_pos(item_path: str, global_coordinates: bool = False) -> float:
    """Returns the horizontal position of the given interface item in canvas or global coordinates.

    Args:
        item_path (`str`): The item path of the item to get the horizontal position for. 
        global_coordinates (`bool`, optional): When set to `True`, the position is returned in global window space. When set to `False`, the position is returned in canvas space. Defaults to `False`.

    Returns:
        float: The horizontal position of the item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_pos.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_secondary(item_path: str) -> float:
    """Returns the the secondary numeric value of an interface item.

    Some interface items have two numeric values, e.g., the 2D control for a light. This function returns the secondary value, e.g., the y-component of a 2D control. This function cannot to be used to get modifier states.

    .. note::

        The :func:`get_mod<zbrush.commands.get_mod>` function returns the modifier state of an item, e.g., if the x, y, or z modifier of a deformation slider is active.

    Args:
        item_path (`str`): The item path of the item to get the secondary value for.

    Returns:
        float: The secondary value of the item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_secondary.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_status(item_path: str) -> bool:
    """Returns the if an interface item is currently enabled or disabled, i.e., if it is greyed out or not.

    .. note::

        To get the value of an item, e.g., if a toggle button is pressed or not, use :func:`get<zbrush.commands.get>`.

    Args:
        item_path (`str`): The item path of the item to get the status for.

    Returns:
        bool: `True` if the item is enabled, `False` if it is disabled.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_status.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_stroke_info(stroke: Stroke, info: int, index: int = 0) -> float:
    """Gets the given 'info' property for the passed stroke object.

    Args:
        stroke (:class:`Stroke`): The stroke object to retrieve information from.
        info (`int`): The property to retrieve.

            ====== =================================================================================
            `0`    The number of points in the stroke.
            `1`    The horizontal position of the indexed point in canvas space. Requires an index.
            `2`    The vertical position of the indexed point in canvas space. Requires an index.
            `3`    The pen pressure of the indexed point. Requires an index.
            `4`    The left bounds (i.e., `min_x`) of the stroke bounding box in canvas space.
            `5`    The top bounds (i.e., `min_y`) of the stroke bounding box in canvas space.
            `6`    The right bounds (i.e., `max_x`) of the stroke bounding box in canvas space.
            `7`    The bottom bounds (i.e., `max_y`) of the stroke bounding box in canvas space.
            `8`    The 'maximum radius' of the stroke, capturing the largest distance from the start of the stroke.
            `9`    The index of the point with is farthest from the start of the stroke.
            `10`   The largest horizontal delta between a point and the starting point of the stroke.
            `11`   The largest vertical delta between a point and the starting point of the stroke.
            `12`   The total length of the stroke.
            `13`   The 'twirl count', an internal value that to some degree expresses how straight a stroke is. 
            `14`   The deduced delta z value of the stroke. This is an internal value of no use for third parties.
            `15`   The modifier key that has been pressed while the given stroke point was recorded.
            ====== =================================================================================

        index (`int`, optional): The zero-based index of the point to retrieve information for.
            Only relevant for information types that are per-point, e.g., position or pressure. Defaults to `0`.

    Returns:
        float: The value of the requested property.

    Example:
        .. code-block:: Python

            from zbrush import commands as zbc

            # Get the last drawn stroke.
            last: zbc.Stroke = zbc.get_last_stroke()

            # Define some symbols for better readability.
            ID_POINT_COUNT: int = 0
            ID_HORZ_POS: int = 1
            ID_VERT_POS: int = 2
            ID_PRESSURE: int = 3
            ID_MIN_X: int = 4
            ID_MIN_Y: int = 5
            ID_MAX_X: int = 6
            ID_MAX_Y: int = 7

            # Get the point count and bounding box of the stroke.
            count: int = int(zbc.get_stroke_info(last, ID_POINT_COUNT))
            min_x: float = round(zbc.get_stroke_info(last, ID_MIN_X), 2)
            min_y: float = round(zbc.get_stroke_info(last, ID_MIN_Y), 2)
            max_x: float = round(zbc.get_stroke_info(last, ID_MAX_X), 2)
            max_y: float = round(zbc.get_stroke_info(last, ID_MAX_Y), 2)
            print(f"Last stroke has {count} points and the bounding box ({min_x}, {min_y}, {max_x}, {max_y})")

            # Strokes can have many points, so we are going only to print information for every 10th point.
            for i in range(0, count, 10):
                pos: tuple[float, float] = (
                    round(zbc.get_stroke_info(last, ID_HORZ_POS, i), 2),
                    round(zbc.get_stroke_info(last, ID_VERT_POS, i), 2),
                )
                pressure: float = round(zbc.get_stroke_info(last, ID_PRESSURE, i), 2)
                print(f"    Point {i} at {pos} with the pressure {pressure}.")
                """
    ...


def get_subtool_count(index: int = -1) -> int:
    """Returns the number of sub-tools in the specified tool index.

    Args:
        index (`int`, optional): The zero-based index of the tool to get the sub-tool count for. Will return the sub-tool count for the active tool when `-1` is passed. Defaults to `-1`.

    Returns:
        int: The total number of sub-tools in the specified tool.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_subtool_count.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_subtool_folder_index(index: int = -1) -> int:
    """Returns the index of the folder the specified sub-tool is contained in.

    Args:
        index (`int`, optional): The zero-based index of the sub-tool to get the folder index for. Will return the folder index for the active sub-tool when `-1` is passed. Defaults to `-1`.

    Returns:
        int: The zero-based index of the sub-tool folder the specified sub-tool is contained in.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_subtool_folder_index.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_subtool_folder_name(index: int = -1) -> str:
    """Returns the name of the folder the specified sub-tool is contained in.

    Args:
        index (`int`, optional): The zero-based index of the sub-tool to get the folder name for. Will return the folder name for the active sub-tool when `-1` is passed. Defaults to `-1`.

    Returns:
        str: The name of the folder the specified sub-tool is contained in.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_subtool_folder_index.0.py
            :language: python
            :lines: 7-


    """
    ...


def get_subtool_id(index: int = -1, subToolIndex: int = -1) -> int:
    """Returns the unique ID for the given sub-tool index and tool index.

    Args:
        index (`int`, optional): The zero-based index of the tool within which to get a sub-tool ID. Will return a sub-tool ID within the active tool when `-1` is passed. Defaults to `-1`.
        subToolIndex (`int`, optional): The zero-based index of the sub-tool to get the ID for. Will return the ID for the active sub-tool when `-1` is passed. Defaults to `-1`.

    Returns:
        int: The unique ID of the specified sub-tool.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_subtool_id.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_subtool_status(index: int = -1) -> int:
    """Returns the status flag for the enabled options of a sub-tool in the active tool.

    The options referred to are the icons visible on top of a sub-tool list item in the 'Tool:Subtool' sub-tools list view.

    .. include:: /partials/api_flags.rst

    Args:
        index (`int`, optional): The zero-based index of the sub-tool to get the status for. Will return the status for the active sub-tool when `-1` is passed. Defaults to `-1`.

    Returns:
        int: The status flag for the options for the specified sub-tool. With the following masks:

            =========== =============================================
            `0x0001`    If the eye of the sub-tool is enabled.
            `0x0002`    If the eye of the folder of the sub-tool is enabled.
            `0x0010`    If the volume add mode of the sub-tool is enabled.
            `0x0020`    If the volume subtract mode of the sub-tool is enabled.
            `0x0040`    If the volume clip mode of the sub-tool is enabled.
            `0x0080`    If the sub-tool is marked as a volume start.
            `0x0400`    If the folder of the sub-tool is closed.
            `0x0800`    If the folder of the sub-tool is opened.
            =========== =============================================

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_subtool_status.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_timeline_time() -> float:
    """Returns the current time.

    The 'current' time is the position of the playhead in the timeline.

    .. include:: /partials/api_zbrush_document_time.rst

    Returns:
        float: The current time as a normalized document time value.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_timeline_time.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_title(item_path: str, full_path: bool = False) -> str:
    """Returns the title of the specified interface item.

    This effectively just returns the last component of an item path.

    Args:
        item_path (`str`): The item path of the item to get the title for.
        full_path (`bool`, optional): If set to `True`, `item_path` is treated as a full path to the item, otherwise it is treated as a relative path. Defaults to `False`.

    Returns:
        str: The title of the specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_title.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_tool_count() -> int:
    """Returns the total number of available tools.

    .. note::

        The tool count directly corresponds to the available tool indices.

    Returns:
        int: The total number of available tools.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_tool_count.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_tool_path(index: int = -1) -> str:
    """Returns the label or file path for the specified tool.

    Args:
        index (`int`, optional): The zero-based index of the tool to retrieve the path for. Returns the tool path for the active tool when `-1` is being passed. Defaults to `-1`.

    Returns:
        str: The label or file path for the specified tool:

            - Builtin tools such as the 'Sphere3D' tool will return their label.
            - Runtime user created tools such as a PolyMesh3D 'Sphere3D' tool will also return their label.
            - Tools loaded from disk with will return their absolute file path.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_tool_count.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_transform() -> list[float]:
    """Gets the current tool transform.

    .. include:: /partials/api_zbrush_camera_transform.rst

    Returns:
        list[float]: A nine element list expressing the current tool transform.

        ==== ====================================================
        `0`  The x position of the tool in canvas space. 
        `1`  The y position of the tool in canvas space.
        `2`  The z position of the tool in canvas space.
        `3`  The x scale of the tool in canvas space.
        `4`  The y scale of the tool in canvas space.
        `5`  The z scale of the tool in canvas space.
        `6`  The x rotation of the tool in degrees.
        `7`  The y rotation of the tool in degrees.
        `8`  The z rotation of the tool in degrees.
        ==== ====================================================

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_transform.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_transpose() -> list[float]:
    """Gets current action line values of the current transpose tool.

    An action line is the UI which is enabled when the user selects one of the transpose tools and then disables 
    the 'Transform:Gizmo 3D' option.

    Returns:
        list[float]: A sixteen element list expressing the current transpose action line. 

        ==== ====================================================
        `0`  The x component of the origin of the action line.
        `1`  The y component of the origin of the action line.
        `2`  The z component of the origin of the action line.
        `3`  The x component of the normal of the action line.
        `4`  The y component of the normal of the action line.
        `5`  The z component of the normal of the action line.
        `6`  The length of the action line.
        `7`  The x component of the red axis.
        `8`  The y component of the red axis.
        `9`  The z component of the red axis.
        `10` The x component of the green axis.
        `11` The y component of the green axis.
        `12` The z component of the green axis.
        `13` The x component of the blue axis.
        `14` The y component of the blue axis.
        `15` The z component of the blue axis.
        ==== ====================================================

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_transpose.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_width(item_path: str) -> float:
    """Returns the width in pixels of the specified interface item.

    Args:
        item_path (`str`): The item path of the item to get the width for.

    Returns:
        int: Width in pixels of specified interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_width.0.py
            :language: python
            :lines: 7-

    """
    ...


def get_zsphere(property: int, index: int, sub_index: int) -> float:
    """Gets the specified property for a ZSphere within the currently active ZSpheres tool.

    Args:
        property (`int`): The property to get.

            ==== ==========================
            `0`   The total count of ZSpheres in the tool.
            `1`   The x position of the ZSphere.
            `2`   The y position of the ZSphere.
            `3`   The z position of the ZSphere.
            `4`   The radius of the ZSphere.
            `5`   The color of the ZSphere in ZBrush hex format. 
            `6`   The mask of the ZSphere in the interval `[0, 255]`. `0` means unmasked, `255` means fully masked.
            `7`   The parent index of the ZSphere. The root ZSphere will have a parent index of `-1`. All other ZSpheres will have a parent index greater than or equal to `0`.
            `8`   The last click index. `-1` means no last click.
            `9`   The timestamp of the last edit.
            `10`  The number of children this ZSphere has.
            `11`  The sub-index of a Zsphere.
            `12`  The timestamp count.
            `13`  The timestamp index.
            `14`  The flags of the ZSphere.
            `15`  The twist angle of the ZSphere.
            `16`  The membrane value of the ZSphere.
            `17`  The X resolution of the ZSphere.
            `18`  The Y resolution of the ZSphere.
            `19`  The Z resolution of the ZSphere.
            `20`  The XYZ resolution of the ZSphere.
            `21`  The user value of the ZSphere.
            ==== ==========================

        index (`int`): The index of the ZSphere to query. Must be a value greater or equal than zero.
        sub_index (`int`): The sub-index of the ZSphere to query. Can usually be set to zero.

    Returns:
        float: The value of the specified property for the ZSphere.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.get_zsphere.0.py
            :language: python
            :lines: 7-

    """
    ...


def has_next_filename() -> bool:
    """Tests if a preset file name or path has been set.

    Returns:
        bool: `True` if a preset file name or path has been set for the next load or save operation, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.has_next_filename.0.py
            :language: python
            :lines: 7-

    """
    ...


def hide(item_path: str, show_zoom_rects: bool = False, parent_window: bool = False) -> None:
    """Removes an interface item from the UI without deleting it.

    Args:
        item_path (`str`): The item path of the item to hide.
        show_zoom_rects (`bool`, optional): if to show zoom rectangles for the hidden item. Defaults to `False`.
        parent_window (`bool`, optional): If to also hide the parent window of the item. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.hide.0.py
            :language: python
            :lines: 7-

    """
    ...


def hide_canvas_extras() -> None:
    """Hides overlay elements in the canvas.

    .. note::

        Hidden for now due to being non-functional.

    Example:
        .. code-block::

            from zbrush import commands as zbc

            zbc.hide_canvas_extras()

    """
    ...


def increment_filename(base: str, digits: int = 3, add_copy: bool = False) -> str:
    """Increments a numeric portion in the given file name or path.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    .. warning::

        - This function exists purely for ZScript legacy purposes.
        - The `digits` feature is buggy and can fail to detect/expand an index not fitting the digit length.
        - Use Python's regular expressions and string interpolation instead when you can as you have there more control.

    Args:
        base (`str`): The file name or file path to increment.
        digits (`int`, optional): The number of digits to ensure in the interval `[0, 4]`. Defaults to `3`.
        add_copy (`bool`, optional): Non-functional. 

    Returns:
        str: The file name with its numeric portion being incremented.

    Example:
        .. code-block::

            from zbrush import commands as zbc

            # Increment both a file name and path. Because get extended to the default three digit scheme.
            zbc.increment_filename("image_1.psd") # > "image_002.psd"
            zbc.increment_filename(r"D:\\temp\\file_1.zbr") # > "D:\\temp\\file_002.zbr" (printed as "D:tempfile_002.zbr")
    """
    ...


def interpolate(time: float,
                v1: float | list[float],
                v2: float | list[float],
                v3: float | list[float] | None = None,
                v4: float | list[float] | None = None,
                as_angle: bool = False) -> float | list[float]:
    """Returns the linear, quadratic, or cubic interpolation at the given offset `time`.

    Depending on the number of passed arguments, the function will interpolate linearly, quadratically, or cubically. It can also interpolate piecewise over multiple segments. It uses the standard quadratic Bézier polynomial and the standard cubic Hermite polynomial for the non-linear interpolation modes.

    Args:
        time (`float`): The interpolation offset (which is conventionally labeled as `t`) in the interval `[0, 1]`.
        v1 (`float`): The first control point in linear and quadratic mode, the left tangent in cubic mode.
        v2 (`float`): The second control point in linear and quadratic mode, the first control point in cubic mode.
        v3 (`float`, optional): The bias in cubic mode, the first control point in quadratic mode. Defaults to `None`.
        v4 (`float`, optional): The right tangent in cubic mode. Defaults to `None`.
        as_angle (`bool`, optional): If to interpret the input values as values in degrees (sic!, not radians). This does not entail spherical interpolation but rather a custom clamping algorithm for the four input values and then falls back to the same interpolation polynomials. Is usually not that useful unless one has to replicate exactly this ZBrush 'angle interpolation' behaviour. Defaults to `False`.

    Returns:
        float | list[float]: The interpolated value(s).

    Example:
        .. code-block::

            from zbrush import commands as zbc

            offsets: list[float] = [0.0, 0.2, 0.4, 0.4, 0.8, 1.0] # A a list of interpolation offsets.
            a: float = 0.0 # Start of the interpolation interval.
            b: float = 1.0 # End of the interpolation interval.

            # Simple linear interpolation, we call interpolate(t, a, b).
            result: list[float] = [zbc.interpolate(t, a, b) for t in offsets]
            print(f"Linear: {result}")
            # The output, the values are like this due to floating point precision, 0.2, 0.4, ... are
            # not precisely representable as floating point values and these are the closest values that
            # are representable. Or in other words, mathematically this would be [0, 0.2, 0.4, 0.4, 0.8, 1.0].
            # > [0.0, 0.20000000298023224, 0.4000000059604645, 0.4000000059604645, 0.800000011920929, 1.0]

            # Quadratic interpolation. Here we call interpolate(t, a, bias, b). The values are skewed
            # towards #a because of the bias of 0.25.
            bias: float = 0.25 # The bias of the quadratic interpolation.
            result: list[float] = [zbc.interpolate(t, a, bias, b) for t in offsets]
            print(f"Quadratic: {result}")
            # > [0.0, 0.11999998986721039, 0.2800000011920929, 0.2800000011920929, 0.7200000286102295, 1.0]

            # And finally, cubic interpolation, here the input format is interpolate(ta, a, b, tb). The
            # format is a bit unusual but it is indeed the format. Since we give #a a bias of 0.25 and #b 
            # a bias of 0.0 (because tb == b), we see values stretched out around #a and then approaching 
            # a linear interpolation with #b.
            ta: float = -0.25 # The left tangent of #a, usually a value smaller or equal than #a.
            tb: float = 1.0 # The right tangent of #b, usually a value larger or equal than #b.
            result: list[float] = [zbc.interpolate(t, ta, a, b, tb) for t in offsets]
            print(f"Cubic: {result}")
            # > [0.0, 0.1680000126361847, 0.39400002360343933, 0.39400002360343933, 0.8520000576972961, 1.0]

            # And last but not least, we can also do the same with lists of values. #t will NOT be interpreted 
            # over the length of all segments but rather piecewise. Due to Python's strong iteration features
            # we could also easily do this with list comprehensions ourselves.

            # Linearly interpolate the three segments [0, .25], [.25, .50], and [.50, 1.0] at once. 
            result: list[float] = [zbc.interpolate(t, 
                                                   [0.0,  0.25, 0.5],  # a
                                                   [0.25, 0.50, 1.0])  # b
                                   for t in (0.0, 0.5, 1.0)]
            print(f"Linear list:")
            for item in result:
                print(f"    {item}")
            # [
            #   [0.0, 0.25, 0.5],        # (a, b) at t = 0.0, we get #a of each segment.
            #   [0.125, 0.375, 0.75],    # (a, b) at t = 0.5, we get the average of each segment.
            #   [0.25, 0.5, 1.0]         # (a, b) at t = 1.0, we get #b of each segment.
            # ]

    """
    ...


def is_disabled(item_path: str) -> bool:
    """Tests if the specified interface item is disabled, i.e., not greyed out and not interactable.

    Args:
        item_path (`str`): The item path of the interface item to test for being disabled.

    Returns:
        bool: `True` if the specified interface item is currently disabled, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.is_disabled.0.py
            :language: python
            :lines: 7-

    """
    ...


def is_enabled(item_path: str) -> bool:
    """Tests if the specified interface item is enabled, i.e., not greyed out and interactable.

    Args:
        item_path (`str`): The item path of the interface item to test for being enabled.

    Returns:
        bool: `True` if the specified interface item is currently enabled, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.is_enabled.0.py
            :language: python
            :lines: 7-

    """
    ...


def is_locked(item_path: str) -> bool:
    """Tests if the specified interface item is locked, i.e., not interactable.

    Args:
        item_path (`str`): The item path of the interface item to test for being locked.

    Returns:
        bool: `True` if the specified interface item is currently locked, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.is_locked.0.py
            :language: python
            :lines: 7-

    """
    ...


def is_polymesh3d_solid() -> bool:
    """Returns if the active subtool in the active tool is a solid mesh.

    E.g., when you create a 'Sphere3D' tool, this gives you a 'watertight' mesh and this function would return `True`. If you now would delete a face of that sphere, it would no longer be watertight and this function would return `False`.

    Returns:
        bool: `True` if the active tool is solid mesh, `False` otherwise.

    """
    ...


def is_transpose_shown() -> bool:
    """Returns if a transpose tool is active.

    Returns:
        bool: `True` if a transpose tool is active, `False` otherwise. Which drawing gizmo is activated in the transpose tool, the tranpose line or the 3D gizmo, has no impact on the result of this method.
    """
    ...


def is_unlocked(item_path: str) -> bool:
    """Tests if the specified interface item is unlocked, i.e., interactable.

    Args:
        item_path (`str`): The item path of the interface item to test for being unlocked.

    Returns:
        bool: `True` if the specified interface item is currently unlocked, `False` otherwise.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.is_unlocked.0.py
            :language: python
            :lines: 7-

    """
    ...


def load_stroke(path: str) -> Stroke:
    """Loads a brush stroke from a text file.

    Args:
        path (`str`): The `txt` file to load the stroke data from. This should contain a string representation of a 
            stroke as passed to :meth:`Stroke.__init__`.

    Returns:
        :class:`Stroke`: The loaded brush stroke.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.load_stroke.0.py
            :language: python
            :lines: 7-

    """
    ...


def load_strokes(path: str) -> Strokes:
    """Loads a collection of brush strokes from a text file.

    Args:
        path (`str`): The `txt` file to load the stroke data from. This should contain a string representation of a 
            stroke collection as passed to :meth:`Strokes.__init__`.

    Returns:
        :class:`Strokes`: The loaded collection of brush strokes.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.load_strokes.0.py
            :language: python
            :lines: 7-

    """
    ...


def locate_subtool(index: int) -> int:
    """Returns the index of the sub-tool with the given unique ID within the active tool.

    Args:
        index (`int`): The unique ID of the sub-tool to locate.

    Returns:
        int: The index of the located sub-tool, or `-1` if not found.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.locate_subtool.0.py
            :language: python
            :lines: 7-

    """
    ...


def locate_subtool_by_name(name: str) -> int:
    """Returns the index of the sub-tool with the given name within the active tool.

    Args:
        name (`str`): The name of the sub-tool to locate.

    Returns:
        int: The index of the located sub-tool, or `-1` if not found.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.locate_subtool_by_name.0.py
            :language: python
            :lines: 7-

    """
    ...


def lock(item_path: str) -> None:
    """Makes an interface item unresponsive to user interactions.

    .. include:: /partials/api_lock_disable.rst

    Args:
        item_path (`str`): The item path of the interface item to lock.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.lock.0.py
            :language: python
            :lines: 7-

    """
    ...


def make_filename(base: str, index: int, digits: int = 0) -> str:
    """Combines a file name or path with an index, while ensuring a minimum number of digits.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Args:
        base (`str`): The file name or file path to extend.
        index (`int`): The index to append.
        digits (`int`, optional): The number of digits to ensure for the index part. Defaults to `0`.

    Returns:
        str: The generated file name.

    Example:
        .. code-block::

            from zbrush import commands as zbc

            import os

            file_path: str = r"D:\\file.zbr"
            index: int = 2

            # Create a new file name for the index 2 and at least three digits and then do the same
            # for a file path.
            zbc.make_filename("image.psd", index, 3) # > "image_002.psd"
            zbc.make_filename(file_path, index, 3) # > "D:\\file_002.zbr" (printed as "D:file_002.zbr")

            # A more pythonic approach would be to use `os` and string interpolation instead. It is one
            # line more but we have much more control over the result.
            head, ext = os.path.splitext(file_path) # Chop of the extension
            new_path: str = f"{head}_{index:03d}{ext}" # > "D:\\file_002.zbr" (printed as "D:file_002.zbr")

    """
    ...


def maximize(item_path: str, maximize_all: bool = False) -> None:
    """Expands an interface item to its maximum size.

    This function is primarily applicable to palettes and sub-palettes.

    Args:
        item_path (`str`): The item path of the interface item to maximize.
        maximize_all (`bool`, optional): When set to `True`, all sub-palettes will also be maximized. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.maximize.0.py
            :language: python
            :lines: 7-

    """
    ...


def merge_undo() -> None:
    """Not implemented.
    """
    """Merges the current undo item with the previous undo item.
    
    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.merge_undo.0.py
            :language: python
            :lines: 7-

    """
    ...


def message_ok(message: str = '', title: str = '') -> None:
    """Displays a message dialog with a button to accept the message.

    Args:
        message (`str`, optional): The message that will be shown. Defaults to the empty string.
        title (`str`, optional): The title of the message. Defaults to the empty string.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.message_ok.0.py
            :language: python
            :lines: 7-

    """
    ...


def message_ok_cancel(message: str = '', title: str = '') -> bool:
    """Displays a message dialog with buttons to accept or cancel the dialog.

    Args:
        message (`str`, optional): The message that will be shown. Defaults to the empty string.
        title (`str`, optional): The title of the message. Defaults to the empty string.

    Returns:
        bool: `True` if the user clicked 'OK', `False` if the user clicked 'CANCEL'.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.message_ok_cancel.0.py
            :language: python
            :lines: 7-

    """
    ...


def message_yes_no(message: str = '', title: str = '') -> bool:
    """Displays a message dialog with buttons to accept or reject the dialog.

    Args:
        message (`str`, optional): The message that will be shown. Defaults to the empty string.
        title (`str`, optional): The title of the message. Defaults to the empty string.

    Returns:
        bool: `True` if the user clicked 'YES', `False` if the user clicked 'NO'.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.message_yes_no.0.py
            :language: python
            :lines: 7-

    """
    ...


def message_yes_no_cancel(message: str = '', title: str = '') -> int:
    """Displays a message dialog with buttons to accept, reject, or cancel the dialog.

    Args:
        message (`str`, optional): The message that will be shown. Defaults to the empty string.
        title (`str`, optional): The title of the message. Defaults to the empty string.

    Returns:
        int: `1` if the user clicked 'YES', `0` if the user clicked 'NO', `-1` if the user clicked 'CANCEL'.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.message_yes_no_cancel.0.py
            :language: python
            :lines: 7-

    """
    ...


def minimize(item_path: str, minimize_all: bool = False) -> None:
    """Collapses an interface item to its minimum size.

    This function is primarily applicable to palettes and sub-palettes.

    Args:
        item_path (`str`): The item path of the interface item to minimize.
        minimize_all (`bool`, optional): When set to `True`, all sub-palettes will also be minimized. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.minimize.0.py
            :language: python
            :lines: 7-

    """
    ...


def modify(item_path: str, width: int = 0, height: int = 0, icon_path: str = '') -> None:
    """Modifies the height, width, or icon of an script sourced interface item after it has been created.

    .. warning::

        This function is currently broken and does not work as intended.

    .. note::

        This function only works for interface items created via scripting, natively created interface items cannot be modified.

    Args:
        item_path (`str`): The item path of the interface item to modify.
        width (`int`, optional): The new button width as a relative value or a pixel value. Will use the existing width if set to `0`. Defaults to `0`.
        height (`int`, optional): The new button height as a relative value or a pixel value. Will use the existing height if set to `0`. Defaults to `0`.
        icon_path (`str`, optional): The new file path to the button icon. Will keep the existing icon if set to the empty string. Will delete the existing icon if set to `"DeleteIcon"`. Defaults to the empty string.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.modify.0.py
            :language: python
            :lines: 7-

    """
    ...


def new_curves() -> None:
    """Creates a new curves list, deleting any previously created ones in the process.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.new_curves.0.py
            :language: python
            :lines: 7-

    """
    ...


def new_keyframe(time: float | None) -> int:
    """Creates a new keyframe in the active track at the given document time.

    .. include:: /partials/api_zbrush_document_time.rst

    Args:
        time (`float`): The normalized document time at which to create the keyframe or `None` to create a keyframe at the current time.

    Returns:
        int: The zero-based index of the created keyframe or `-1` when an error occured.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.new_keyframe.0.py
            :language: python
            :lines: 7-

    """
    ...


def pixol_pick(component: int, h_position: float, v_position: float) -> float:
    """Returns the specified pixol component for given coordinates.

    Args:
        component (`int`): The component of the pixol to retrieve. With the fields:

            ====== ==================================================
            `0`    The hex color value for the pixol.
            `1`    The Z (depth) value for the pixol (is broken).
            `2`    The red color component for the pixol in the interval `[0, 255]`.
            `3`    The green color component for the pixol in the interval `[0, 255]`.
            `4`    The blue color component for the pixol in the interval `[0, 255]`.
            `5`    The material index for the pixol in the interval `[0, 255]`.
            `6`    The x component of the normal for the pixol in the interval `[-1, 1]`.
            `7`    The y component of the normal for the pixol in the interval `[-1, 1]`.
            `8`    The z component of the normal for the pixol in the interval `[-1, 1]`.
            ====== ==================================================

        h_position (`float`): The horizontal coordinate in canvas space to sample.
        v_position (`float`): The vertical coordinate in canvas space to sample.

    Returns:
        float: The value of the specified pixol component at the given coordinates.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.pixol_pick.0.py
            :language: python
            :lines: 7-

    """
    ...


def press(item_path: str) -> None:
    """Brings a button into its pressed state.

    .. note::

        This functions is only applicable to buttons. Switches must be :func:`toggled <zbrush.commands.toggle>`. All UI elements can also be set via :func:`set <zbrush.commands.set>`.

    Args:
        item_path (`str`): The item path of the interface item to press.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.press.0.py
            :language: python
            :lines: 7-

    """
    ...


def press_key(shortcut: str, fn: Callable = None, h_position: float = -1.0, v_position: float = -1.0) -> None:
    """Simulates the user pressing a singular key or shortcut.

    .. include:: /partials/api_shortcuts.rst

    .. note::

        Does not work, hidden for now.

    Args:
        shortcut (`str`): The shortcut or key press to simulate.
        fn (`Callable`, optional): A callback function to execute while the key or shortcut is pressed. Defaults to `None`.
        h_position (`float`, optional): The horizontal cursor position prior to simulate while the key is pressed. Pass `-1.0` to not change the current cursor position. Defaults to `-1.0`.
        v_position (`float`, optional): The vertical cursor position prior to simulate while the key is pressed. Pass `-1.0` to not change the current cursor position. Defaults to `-1.0`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.press_key.0.py
            :language: python
            :lines: 7-

    """
    ...


def query_mesh3d(property: int, index: int | None = None) -> list[float]:
    """Gets mesh and UV information for the active tool and its sub-tools.

    Args:
        property (`int`): The mesh property to query.

            ==== ================================================================
            `0`  The total point count of the mesh.
            `1`  The total face count of the mesh.
            `2`  The bounding box of the mesh in the shape `(-x, -y, -z, +x, +y, +z)`.
            `3`  The uv bounding box for the mesh in the shape `(left, top, right, bottom)`.
            `4`  The ID of the first UV tile.
            `5`  The ID of the next UV tile.
            `6`  The polygon count of the given UV tile.
            `7`  The area of the given UV tile.
            `8`  The area of the full mesh.
            ==== ================================================================

        index (`int`): Specifies an element or mode when querying some properties. Defaults to `None`.

            ================= ================================================================
            `Bounding Box`    0: The visible bounding box of the current sub-tool.
            `Bounding Box`    1: The full bounding box of the current sub-tool.
            `Bounding Box`    2: The visible bounding box of all visible sub-tools.
            `Bounding Box`    3: The full bounding box of all sub-tools.
            `Next UV Tile`    The id of the uv tile to get the next tile for.
            `UV Tile Count`   The id of the uv tile to get the polygon count for.
            `UV Tile Area`    The id of the uv tile to get the area for.
            ================= ================================================================

    Returns:
        list[float]: The queried mesh property value(s), the shape depends on the property.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.query_mesh3d.0.py
            :language: python
            :lines: 7-

    """
    ...


def randomize(seed: int) -> None:
    """Reseeds the random number generator of ZBrush.

    Args:
        seed (`int`): The new seed value in the interval `[0, 32767]`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.randomize.0.py
            :language: python
            :lines: 7-

    """
    ...


def reset(item: int = 0, version: float = 1.5) -> int:
    """Brings the ZBrush into a default state associated with a particular version.

    This function can be useful to ensure a known state of the interface before running a script. As useful as this function is, it is better not to rely on an implicit interface state and instead explicitly set all relevant interface items to the desired state via :func:`set <zbrush.commands.set>`, :func:`press <zbrush.commands.press>`, :func:`toggle <zbrush.commands.toggle>`, etc. Recording a macro will implicitly call this function at the start of the macro to ensure a known state.

    .. seealso::

        :func:`config <zbrush.commands.config>` loads a ZBrush configuration associated with a particular version which does not require user interaction.

    Args:
        item (`int`, optional): The parts of the interface to reset. Defaults to `0`.

            ====== ================================================================
            `0`    Resets everything.
            `1`    Resets the interface into the default state.
            `2`    Resets the document into a default state.
            `3`    Resets the tools into their default state.
            `4`    Resets the lights into their default state.
            `5`    Resets the materials into their default state.
            `6`    Resets the stencils into their default state.
            ====== ================================================================

        version (`float`, optional): The version to reset to. Defaults to `1.5`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.reset.0.py
            :language: python
            :lines: 7-

    """
    ...


def resolve_path(path: str) -> str:
    """Makes the given relative path absolute in relation to the directory of the executing Python module.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Args:
        path (`str`): Local File Name

    Returns:
        str: The absolute path to the file.

    Example:
            .. literalinclude:: /../../examples/fragments/zbrush.commands.resolve_path.0.py
                :language: python
                :lines: 7-

    """
    ...


def rgb(r: int, g: int, b: int) -> int:
    """Returns an RGB color in the int-format used by many functions in the ZBrush API.

    The formula to calculate a int value from an RGB triplet is `R * 65536 + G * 256 + B`.

    Args:
        r (`int`): The red component to encode in the interval `[0, 255]`.
        g (`int`): The green component to encode in the interval `[0, 255]`.
        b (`int`): The blue component to encode in the interval `[0, 255]`.

    Returns:
        int: The encoded RGB color value.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.rgb.0.py
            :language: python
            :lines: 7-

    """
    ...


def select_subtool(index: int = -1) -> int:
    """Activates the sub-tool with the given index within the active tool.

    Args:
        index (`int`, optional): The zero-based index of the sub-tool to select.

    Returns:
        int: `0` on success, `-1` when an error occurred.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.select_subtool.0.py
            :language: python
            :lines: 7-

    """
    ...


def select_tool(index: int) -> int:
    """Selects the tool with the given index.

    Args:
        index (`int`): The zero-based index of the tool to select.

    Returns:
        int: `0` on success, `-1` when an error occurred.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.select_tool.0.py
            :language: python
            :lines: 7-

    """
    ...


def set(item_path: str, h_value: float | None = None, v_value: float | None = None) -> None:
    """Sets the current numeric values of an interface item.

    The primary value is the 'obvious' value most items have. E.g., the state of a switch button, the value of a slider. But some items also have a secondary value when their state cannot be expressed by a singular numeric value. E.g., a 2D gadget has an x- and a y-component, which can be set via the primary and secondary value.

    Args:
        item_path (`str`): The item path of the item to set the values for.
        h_value (`float`, optional): The primary value to set. If set to `None`, the value will not be changed. Defaults to `None`.
        v_value (`float`, optional): The secondary value to set. If set to `None`, the value will not be changed. Defaults to `None`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_active_track_index(track_index: int) -> int:
    """Sets active track as selected in the 'Movie > Timeline Tracks' palette by the given index.

    Args:
        track_index (`int`): The index of the track to activate. `0` is the main track.

    Returns:
        int: `0` on success, `-1` when an error occurred.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_active_track_index.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_canvas_pan(h: float, v: float) -> None:
    """Sets the offset of the for drawing used canvas area in relation to the visible canvas area on the screen.

    This function is only useful when a canvas zoom has been set via :func:`set_canvas_zoom<zbrush.commands.set_canvas_zoom>` and the canvas is therefore larger than the visible canvas area.

    .. warning::

        This does not set the camera offset, use :func:`set_transform<zbrush.commands.set_transform>` for that.

    Args:
        h (`float`): The horizontal offset in canvas space. `0` is the left edge of the document.
        v (`float`): The vertical offset in canvas space. `0` is the top edge of the document.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_canvas_pan.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_canvas_zoom(zoom_factor: float) -> None:
    """Sets the zoom factor of the canvas, scaling the visible canvas area in relation to the actual canvas size.

    .. warning::

        This does not set the camera zoom, use :func:`set_transform<zbrush.commands.set_transform>` for that.

    Args:
        zoom_factor (`float`): The new canvas zoom factor, either making the drawn canvas and each pixol in it smaller than the actual canvas (values below `1.0`) or larger than the actual canvas (values above `1.0`). The value `1.0` means that each pixol is shown at its actual size.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_canvas_zoom.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_color(r: int, g: int, b: int) -> None:
    """Sets  the primary color picker used for the brush color in drawing mode and the mesh color in edit mode.

    This is the color that is usually shown in the color picker in the left sidebar of the canvas.

    Args:
        r (`int`): The new red component of the color in the interval `[0, 255]`.
        g (`int`): The new green component of the color in the interval `[0, 255]`.
        b (`int`): The new blue component of the color in the interval `[0, 255]`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_color.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_hotkey(item_path: str, hotkey: str) -> None:
    """Sets the hotkey of the specified interface item.

    Args:
        item_path (`str`): The item path of the interface item to set the hotkey for.
        hotkey (`str`): The hotkey to set.

            .. include:: /partials/api_shortcuts.rst

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_hotkey.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_keyframe_time(frame_index: int, time: float) -> int:
    """Sets the relative document time of the keyframe at the given index.

    Args:
        frame_index (`int`): The zero-based index of the keyframe for which to set the normalized document time.
        time (`float`): The normalized document time in the range `[0, 1]` to set.

    Returns:
        int: The index of the keyframe that was modified or `-1` if the operation failed.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_keyframe_time.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_max(item_path: str, value: float) -> None:
    """Sets the maximum possible numeric the given script generated interface item can take.

    .. warning::

        This function only works for interface items created via scripting, natively created interface items cannot be modified.

    Args:
        item_path (`str`): The item path of the item to set the maximum possible value for.
        value (`float`): The new maximum value the item can take.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_max.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_min(item_path: str, value: float) -> None:
    """Sets the minimum possible numeric the given script generated interface item can take.

    .. warning::

        This function only works for interface items created via scripting, natively created interface items cannot be modified.

    Args:
        item_path (`str`): The item path of the item to set the minimum possible value for.
        value (`float`): The new minimum value the item can take.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_min.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_mod(item_path: str, value: float) -> None:
    """Sets the modifiers state of the given script generated interface item.

    .. include:: /partials/api_modifiers.rst

    Args:
        item_path (`str`): The item path of the item to set the modifiers for.
        value (`float`): The new modifiers state to set.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_mod.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_next_filename(path: str = '', template_path: str = '') -> None:
    """Presets the file path or name used for the next load or save operation.

    When a file name is set, only the name will be set in load or save operations. When a full file path is given, that dialog will use that full path.

    .. include:: /partials/api_zbrush_string_bug_backslash.rst

    Args:
        path (`str`, optional): File name including the extension (such as .psd ). If omitted the stored file name will be cleared.
        template_path (`str`, optional): None-functional at the moment.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_next_filename.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_notebar_text(text: str, progress: float = 0.0) -> None:
    """Displays a message and optionally progress indicator in the top section of the ZBrush UI.

    .. note::

        This is the equivalent of a progress bar in other applications, but it is shown at the top of the UI instead of the bottom.

    Args:
        text (`str`): The message that will be shown. 
        progress (`float`, optional): The progress bar value between `0.0` (off) and `1.0` (100%). Defaults to `0.0`.

    Example:
        .. code-block::

            from zbrush import commands as zbc
            import time

            # A long-running task simulation, where we update the notebar text periodically.
            for i in range(1000):
                p: float = i / 1000.0
                zbc.set_notebar_text(f"Script is calculating : {round(100 * p, 2)}%", p)
                time.sleep(0.0025)  # Simulate some work being done

            zbc.set_notebar_text("", 0) # Clear the bar once we are done.

    """
    ...


def set_status(item_name: str, value: bool) -> None:
    """Sets a script-generated interface item as either being responsive or unresponsive to user interactions.

    .. include:: /partials/api_lock_disable.rst

    Args:
        item_path (`str`): The item path of the item to set the status for.
        value (`bool`): `True` to enable the item, `False` to disable it.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_status.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_subtool_status(index: int = -1, value: int = 0) -> None:
    """Sets the status flags for the enabled options of a sub-tool in the active tool.

    The options referred to are the icons visible on top of a sub-tool list item in the 'Tool:Subtool' sub-tools list view.

    .. include:: /partials/api_flags.rst

    Args:
        index (`int`, optional): The zero-based index of the sub-tool to get the status for. Will set the status for the active sub-tool when `-1` is passed. Defaults to `-1`.
        value (`int`, optional): The flag field to set, realizing a toggle logic. I.e., set an unset flag will set it, and setting and already set flag will remove it. With the the following masks:

            =========== =============================================
            `0x0001`    If the eye of the sub-tool is enabled.
            `0x0002`    If the eye of the folder of the sub-tool is enabled.
            `0x0010`    If the volume add mode of the sub-tool is enabled.
            `0x0020`    If the volume subtract mode of the sub-tool is enabled.
            `0x0040`    If the volume clip mode of the sub-tool is enabled.
            `0x0080`    If the sub-tool is marked as a volume start.
            `0x0400`    If the folder of the sub-tool is closed.
            `0x0800`    If the folder of the sub-tool is opened.
            =========== =============================================

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_subtool_status.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_timeline_time(time: float) -> int:
    """Sets the current time.

    The 'current' time is the position of the playhead in the timeline.

    .. include:: /partials/api_zbrush_document_time.rst

    Args:
        time (`float`): The normalized current document time in the interval `[0.0, 1.0]`.

    Returns:
        int: `0` on success, `-1` on failure.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_timeline_time.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_timeline_to_keyframe_time(frame_index: int) -> float:
    """Sets the current time to the time of the keyframe at the given index.

    .. include:: /partials/api_zbrush_document_time.rst

    Args:
        frame_index (`int`): The zero-based index of the keyframe to set the current time to.

    Returns:
        float: The normalized document time of the specified keyframe to which the current time has been set. Or `-1` when an error occured.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_timeline_to_keyframe_time.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_tool_path(index: int, path: str) -> int:
    """Sets the name or file path of the specified tool.

    Args:
        index (`int`): The zero-based index of the tool to set the path for.
        path (`str`): The new file path or name of the tool. Path extensions (such as .ztl) will be omitted.

    Returns:
        int: `0` on success, `-1` when an error occurred.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_tool_path.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_transform(x_position: float | None = None, y_position: float | None = None, z_position: float | None = None, x_scale: float | None = None, y_scale: float | None = None, z_scale: float | None = None, x_rotate: float | None = None, y_rotate: float | None = None, z_rotate: float | None = None) -> None:
    """Sets the current tool transform.

    .. include:: /partials/api_zbrush_camera_transform.rst

    Args:
        x_position (`float`, optional): The new x position of the tool in canvas space.
        y_position (`float`, optional): The new y position of the tool in canvas space.
        z_position (`float`, optional): The new z position of the tool in canvas space.
        x_scale (`float`, optional): The new x scale of the tool in canvas space.
        y_scale (`float`, optional): The new y scale of the tool in canvas space.
        z_scale (`float`, optional): The new z scale of the tool in canvas space.
        x_rotate (`float`, optional): The new x rotation of the tool in degrees.
        y_rotate (`float`, optional): The new y rotation of the tool in degrees.
        z_rotate (`float`, optional): The new z rotation of the tool in degrees.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_transform.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_transpose(x_start: float | None = None, y_start: float | None = None, z_start: float | None = None, x_end: float | None = None, y_end: float | None = None, z_end: float | None = None, length: float | None = None, x_red: float | None = None, y_red: float | None = None, z_red: float | None = None, x_green: float | None = None, y_green: float | None = None, z_green: float | None = None, x_blue: float | None = None, y_blue: float | None = None, z_blue: float | None = None) -> None:
    """Sets current action line values of the current transpose tool.

    An action line is the UI which is enabled when the user selects one of the transpose tools and then disables 
    the 'Transform:Gizmo 3D' option.

    Args:
        x_start (`float`, optional): The x component of the origin of the action line.
        y_start (`float`, optional): The y component of the origin of the action line.
        z_start (`float`, optional): The z component of the origin of the action line.
        x_end (`float`, optional): The x component of the normal of the action line.
        y_end (`float`, optional): The y component of the normal of the action line.
        z_end (`float`, optional): The z component of the normal of the action line.
        length (`float`, optional): The length of the action line.
        x_red (`float`, optional): The x component of the red axis.
        y_red (`float`, optional): The y component of the red axis.
        z_red (`float`, optional): The z component of the red axis.
        x_green (`float`, optional): The x component of the green axis.
        y_green (`float`, optional): The y component of the green axis.
        z_green (`float`, optional): The z component of the green axis.
        x_blue (`float`, optional): The x component of the blue axis.
        y_blue (`float`, optional): The y component of the blue axis.
        z_blue (`float`, optional): The z component of the blue axis.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_transpose.0.py
            :language: python
            :lines: 7-

    """
    ...


def set_zsphere(property: int, index: int, value: float) -> int:
    """Gets the specified property for a ZSphere within the currently active ZSpheres tool.

    .. warning::

        Editing ZSphere operations always must happen in the context of a :func:`edit_zsphere <zbrush.commands.edit_zsphere>` call.

    Args:
        property (`int`): The property to set.

            ==== ==========================
            `1`   The x position of the ZSphere.
            `2`   The y position of the ZSphere.
            `3`   The z position of the ZSphere.
            `4`   The radius of the ZSphere.
            `5`   The color of the ZSphere in ZBrush hex format. 
            `6`   The mask of the ZSphere in the interval `[0, 255]`. `0` means unmasked, `255` means fully masked.
            `7`   The parent index of the ZSphere. The root ZSphere will have a parent index of `-1`. All other ZSpheres will have a parent index greater than or equal to `0`.
            `9`   The timestamp of the last edit.
            `14`  The flags of the ZSphere.
            `15`  The twist angle of the ZSphere.
            `16`  The membrane value of the ZSphere.
            `17`  The X resolution of the ZSphere.
            `18`  The Y resolution of the ZSphere.
            `19`  The Z resolution of the ZSphere.
            `20`  The XYZ resolution of the ZSphere.
            `21`  The user value of the ZSphere.
            ==== ==========================

            The following properties can NOT be set:

            ==== ==========================
            `0`   The total number of ZSpheres in the current tool.
            `8`   The last click index. `-1` means no last click.
            `10`  The number of children this ZSphere has.
            `11`  The sub-index of a Zsphere.
            `12`  The timestamp count.
            `13`  The timestamp index.
            ==== ==========================

        index (`int`): The index of the ZSphere to set. Must be a value greater or equal than zero.
        value (`float`): The new value of the property to set. All values are expressed as floats.

    Returns:
        int: The result of the operation. `0` indicates success, while `-1` indicates failure.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.set_zsphere.0.py
            :language: python
            :lines: 7-

    """
    ...


def show(item_path: str, show_zoom_rects: bool = False, parent_window: bool = False) -> None:
    """Scrolls to or shows the given palette or script generated interface item.

    This function can be used in two ways:

    - Palettes: When the given `item_path` refers to a palette or sub-palette, the palette will be shown. This either means scroling to the palette when it is docked in one of the docks, or opening it as a floating palette under the cursor when it is not docked. This works both for native palettes such as 'Draw' or 'Tool' as well as for script generated palettes such as `ZScript:Foo` in the example below.
    - Script generated items: When the given `item_path` refers to a script generated non-palette interface item such as a button, slider, or similar, the function will ensure that the item is visible when it before has been hidden via :func:`hide<zbrush.commands.hide>`. This will not work for native buttons, sliders, etc.

    Args:
        item_path (`str`): The palette to show.
        show_zoom_rects (`bool`, optional): Non-functional at the moment.
        parent_window (`bool`, optional): If to apply the operation also to the palette hotsing `item_path`. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.show.0.py
            :language: python
            :lines: 7-

    """
    ...


def show_actions(value: int) -> None:
    """Enables or disables script interface actions being drawn in the UI.

    Before carrying out a series of scripted UI actions with :func:`press<zbrush.commands.press>`, :func:`unpress<zbrush.commands.unpress>`, :func:`toggle<zbrush.commands.toggle>`, or similar functions, this function can be called to disable the visual feedback of these actions to the user. Pure data setters such as :func:`set<zbrush.commands.set>` do not require this.

    Args:
        value (`int`): The new state of the action drawing. Pass `0` to disable action drawing, and `1` to enable it again.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.show_actions.0.py
            :language: python
            :lines: 7-

    """
    ...


def show_canvas_extras() -> None:
    """Shows overlay elements in the canvas.

    .. note::

        Hidden for now due to being non-functional.

    Example:
        .. code-block::

            from zbrush import commands as zbc

            zbc.show_canvas_extras()

    """
    ...


def show_note(text: str, item_path: str = '', display_duration: float = 0.0, bg_color: int = -1, distance_to_ui_item: int = 48, preferred_width: int = 400, fill_color: int = -1, frame_h_size: float = 1.0, frame_v_size: float = 1.0, frame_left_side: float = 0.0, frame_top_side: float = 0.0, icon_path: str = '') -> int:
    """Displays a custom note dialog with the controls defined before the call to this function.

    .. note::

        Notes are ZBrush terminology for modal dialogs.

    Args:
        text (`str`): The title of the dialog.
        item_path (`str`, optional): Has no effect.
        display_duration (`float`, optional): The manner in which the note is displayed. Defaults to `0`.

            ==== ==========================
            `0`  The note is shown immediately and will stay on screen until the user clicks a button.
            `-1` The note is not shown but instead combined with the next `show_note` call that does not use `-1` as the display duration. Multiple notes can be staged like this.
            `>0` Values greater than zero will show the note for the specified number of seconds. After that time the note will disappear automatically.    
            ==== ==========================

        bg_color (`int`, optional): Popup background color. (  0x000000<->0xffffff, default=0x606060, 0=NoBackground )
        distance_to_ui_item (`int`, optional): Has no effect.
        preferred_width (`int`, optional): Has no effect.
        fill_color (`int`, optional): Has no effect.
        frame_h_size (`float`, optional): Has no effect.
        frame_v_size (`float`, optional): Has no effect.
        frame_left_side (`float`, optional): Has no effect.
        frame_top_side (`float`, optional): Has no effect.
        icon_path (`str`, optional): Displays an icon next to the dialog title (`text`). Will display no icon when an empty string is passed. Defaults to the empty string.

    Returns:
        int: The index of the button that was pressed by the user to close the dialog.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.show_note.0.py
            :language: python
            :lines: 7-

    """
    ...


def stroke(item_path: str, stroke: Stroke) -> None:
    """Emulates a brush stroke within an interface item.

    This function is not meant for emulating a brush stroke in the canvas, use :func:`canvas_stroke <zbrush.commands.canvas_stroke>` for that. This function is meant for emulating a brush stroke in interface items and of very limited use. Functions like :func:`set <zbrush.commands.set>`, :func:`press <zbrush.commands.press>`, or :func:`click <zbrush.commands.click>` are usually the better choice for emulating user interactions in the interface.

    Args:
        item_path (`str`): The item path of the interface item to emulate the stroke in.
        stroke (`zbrush.Stroke`): The stroke to carry out on the interface item.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.stroke.0.py
            :language: python
            :lines: 7-

    """
    ...


def system_info() -> str:
    """Returns a string containing the system information.

    .. note::

        The content of the string depends on the OS and CPU architecture. It might contain both CPU
        and RAM information, for CPUs with an overly long system description, this string might be
        truncated and contain no RAM information.

    Returns:
        str: The system information string.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.system_info.0.py
            :language: python
            :lines: 7-

    """
    ...


def toggle(item_path: str) -> None:
    """Toggles the state of a switch.

    Args:
        item_path (`str`): The item path of the switch to toggle.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.toggle.0.py
            :language: python
            :lines: 7-

    """
    ...


def un_press(item_path: str) -> None:
    """Removes the pressed state of a button.

    .. note::

        This functions is only applicable to buttons. Switches must be :func:`toggled <zbrush.commands.toggle>`. All UI elements can also be set via :func:`set <zbrush.commands.set>`.

    Args:
        item_path (`str`): The item path of the interface item to unpress.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.un_press.0.py
            :language: python
            :lines: 7-

    """
    ...


def unlock(item_path: str) -> None:
    """Makes an interface item responsive to user interactions.

    .. include:: /partials/api_lock_disable.rst

    Args:
        item_path (`str`): The item path of the interface item to lock.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.unlock.0.py
            :language: python
            :lines: 7-

    """
    ...


def update(repeat_count: int = 1, redraw_ui: bool = False) -> None:
    """Forces ZBrush to update its internal state and optionally redraw the UI.

    Args:
        repeat_count (`int`, optional): How often ZBrush should update its internal state in a row. Defaults to `1`.
        redraw_ui (`bool`, optional): If to redraw the UI after updating the internal state. Defaults to `False`.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.update.0.py
            :language: python
            :lines: 7-

    """
    ...


def zbrush_info(info: int) -> float:
    """Returns selected information about the running ZBrush instance.

    Args:
        info (`int`): The type of information to retrieve:

            ==== ==========================
            `0`  ZBrush version number.
            `1`  Float value describing the type of ZBrush version: Demo (`0`), Beta (`1`), or Full Version (`2`).
            `2`  The runtime duration of this instance in seconds.
            `3`  The current physical memory usage.
            `4`  The current virtual memory usage.
            `5`  The currently free memory.
            `6`  The operating system: PC (`0`), Mac (`1`), or MacOSX (`2`).
            `7`  The unique session ID.
            `8`  The total amount of RAM in bytes (does not work properly).
            `9`  The current year.
            `10` The current month.
            `11` The current day.
            `12` The current hour.
            `13` The current minutes.
            `14` The current seconds.
            `15` The current day of the week.
            `16` The bit depth of the CPU.
            ==== ==========================

    Returns:
        float: The requested information value.

    Example:
        .. literalinclude:: /../../examples/fragments/zbrush.commands.zbrush_info.0.py
            :language: python
            :lines: 7-

    """
    ...
