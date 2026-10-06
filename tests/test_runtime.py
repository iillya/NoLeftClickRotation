"""Regression tests with every host and Win32 call replaced by test doubles.

These tests never load ZBrush, install a native hook, or generate mouse input.
Run with: python -m unittest discover -s tests -v
"""

import ctypes
import os
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "NoLeftClickRotation.py"
EDIT = "Transform:Edit"
CAMERA = "Draw:Lock Camera"


class Host:
    HWND = 100

    def __init__(self, owner_thread=7):
        self.owner_thread = owner_thread
        self.current_thread = 7
        self.values = {EDIT: True, CAMERA: False}
        self.events = []
        self.hooks = {}
        self.timers = {}
        self.physical_keys = {}
        self.swapped = False
        self.kill_ok = True
        self.remove_ok = True
        self.timer_ok = True
        self.native_handler = None
        self.zbc = ModuleType("zbrush.commands")
        self.zbc.exists = mock.Mock(side_effect=lambda path: path in self.values)
        self.zbc.get = mock.Mock(side_effect=lambda path: self.values[path])
        self.zbc.set = mock.Mock(side_effect=self.set_control)
        self.zbc.toggle = mock.Mock(side_effect=self.toggle_control)
        self.zbc.close = mock.Mock(side_effect=self.close_control)
        self.zbc.add_subpalette = mock.Mock(side_effect=self.add_palette)
        self.zbc.add_switch = mock.Mock(side_effect=self.add_switch)
        self.zbc.add_button = mock.Mock(side_effect=self.add_button)
        self.zbc.set_status = mock.Mock()
        self.zbc.set_notebar_text = mock.Mock()
        self.user32 = SimpleNamespace(
            EnumWindows=mock.Mock(side_effect=self.enum_windows),
            GetClassNameW=mock.Mock(side_effect=self.class_name),
            GetWindowThreadProcessId=mock.Mock(side_effect=self.window_thread),
            SetTimer=mock.Mock(side_effect=self.set_timer),
            KillTimer=mock.Mock(side_effect=self.kill_timer),
            GetAsyncKeyState=mock.Mock(side_effect=lambda key: self.physical_keys.get(key, 0)),
            GetSystemMetrics=mock.Mock(side_effect=lambda metric: int(self.swapped)),
        )
        self.comctl32 = SimpleNamespace(
            SetWindowSubclass=mock.Mock(side_effect=self.install_hook),
            RemoveWindowSubclass=mock.Mock(side_effect=self.remove_hook),
            DefSubclassProc=mock.Mock(side_effect=self.forward),
        )
        self.kernel32 = SimpleNamespace(
            GetCurrentThreadId=mock.Mock(side_effect=lambda: self.current_thread),
            GetUserDefaultUILanguage=mock.Mock(return_value=0x0409),
        )
        self.libraries = {
            "user32": self.user32,
            "comctl32": self.comctl32,
            "kernel32": self.kernel32,
        }
        package = ModuleType("zbrush")
        package.commands = self.zbc
        self.patches = [
            mock.patch.dict("sys.modules", {"zbrush": package, "zbrush.commands": self.zbc}),
            mock.patch.object(ctypes, "WinDLL", side_effect=lambda name, **kw: self.libraries[name], create=True),
            mock.patch.object(ctypes, "windll", SimpleNamespace(kernel32=self.kernel32), create=True),
            mock.patch.object(ctypes, "WINFUNCTYPE", side_effect=lambda *args: lambda function: function, create=True),
            mock.patch.object(os, "startfile", side_effect=AssertionError("External launch forbidden in tests"), create=True),
        ]
        for patch in self.patches:
            patch.start()
        self.namespace = {"__file__": str(SCRIPT), "__name__": "no_left_click_rotation_test"}

    def close(self):
        for patch in reversed(self.patches):
            patch.stop()

    def load(self, same_globals=True):
        if not same_globals:
            self.namespace = {"__file__": str(SCRIPT), "__name__": "no_left_click_rotation_test"}
        exec(compile(SCRIPT.read_text(encoding="utf-8-sig"), str(SCRIPT), "exec"), self.namespace)
        return self.namespace

    def set_control(self, path, value):
        self.events.append(("set", path, bool(value)))
        self.values[path] = bool(value)

    def toggle_control(self, path):
        self.events.append(("toggle", path))
        self.values[path] = not self.values[path]

    def close_control(self, path):
        for key in list(self.values):
            if key == path or key.startswith(path + ":"):
                del self.values[key]

    def add_palette(self, path, **kwargs):
        self.values[path] = False

    def add_switch(self, path, value, *args, **kwargs):
        self.values[path] = bool(value)

    def add_button(self, path, *args, **kwargs):
        self.values[path] = False

    def enum_windows(self, callback, parameter):
        callback(self.HWND, parameter)
        return True

    @staticmethod
    def class_name(hwnd, buffer, capacity):
        buffer.value = "ZBrush"
        return len(buffer.value)

    def window_thread(self, hwnd, process_id):
        if process_id is not None:
            process_id._obj.value = os.getpid()
        return self.owner_thread

    def install_hook(self, hwnd, callback, identifier, reference):
        self.events.append(("install", hwnd, callback))
        self.hooks[(hwnd, callback, identifier)] = reference
        return True

    def remove_hook(self, hwnd, callback, identifier):
        self.events.append(("remove", hwnd, callback))
        if self.remove_ok:
            self.hooks.pop((hwnd, callback, identifier), None)
        return self.remove_ok

    def set_timer(self, hwnd, identifier, interval, callback):
        self.events.append(("timer_start", hwnd, identifier))
        if not self.timer_ok:
            return 0
        self.timers[(hwnd, identifier)] = (interval, callback)
        # Window-owned timers must use the requested ID, not this return value.
        return 999

    def kill_timer(self, hwnd, identifier):
        self.events.append(("timer_stop", hwnd, identifier))
        if self.kill_ok:
            self.timers.pop((hwnd, identifier), None)
        return self.kill_ok

    def forward(self, hwnd, message, wparam, lparam):
        self.events.append(("native", message, self.values[CAMERA]))
        if self.native_handler:
            self.native_handler(message)
        return 321

    def message(self, name, wparam=0, lparam=0):
        scope = self.namespace
        message = scope[name] if isinstance(name, str) else name
        return scope["_subclass"](self.HWND, message, wparam, lparam, scope["SUBCLASS_ID"], 0)

    def tick(self):
        return self.message("WM_TIMER", self.namespace["_edit_timer_id"])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.host = Host()
        self.addCleanup(self.host.close)
        self.scope = self.host.load()

    def test_initialization_owns_one_timer_without_timerproc(self):
        self.assertTrue(self.host.values[CAMERA])
        self.assertEqual(len(self.host.hooks), 1)
        self.assertEqual(len(self.host.timers), 1)
        identifier = self.scope["_edit_timer_id"]
        self.assertNotEqual(identifier, 999)
        self.assertEqual(self.host.timers[(Host.HWND, identifier)], (100, None))

    def test_right_gesture_unlocks_before_native_down_and_relocks_after_up(self):
        self.host.events.clear()
        self.assertEqual(self.host.message("WM_RBUTTONDOWN"), 321)
        self.assertEqual(self.host.message("WM_RBUTTONUP"), 321)
        self.assertEqual(self.host.events, [
            ("set", CAMERA, False), ("native", self.scope["WM_RBUTTONDOWN"], False),
            ("native", self.scope["WM_RBUTTONUP"], False), ("set", CAMERA, True),
        ])

    def test_double_click_is_a_second_right_press(self):
        self.host.message("WM_RBUTTONDBLCLK")
        self.assertFalse(self.host.values[CAMERA])
        self.assertTrue(self.scope["_right_down"])
        self.host.message("WM_RBUTTONUP")
        self.assertTrue(self.host.values[CAMERA])

    def test_forward_once_when_preprocessing_raises(self):
        with mock.patch.dict(self.scope, {"_handle_right_down": mock.Mock(side_effect=RuntimeError("pre"))}):
            self.assertEqual(self.host.message("WM_RBUTTONDOWN"), 321)
        self.host.comctl32.DefSubclassProc.assert_called_once()
        self.assertEqual(self.scope["_dispatch_depth"], 0)

    def test_forward_once_when_postprocessing_raises(self):
        with mock.patch.dict(self.scope, {"_handle_right_up": mock.Mock(side_effect=RuntimeError("post"))}):
            self.assertEqual(self.host.message("WM_RBUTTONUP"), 321)
        self.host.comctl32.DefSubclassProc.assert_called_once()

    def test_native_forward_failure_is_not_retried_or_raised(self):
        self.host.comctl32.DefSubclassProc.side_effect = RuntimeError("native failure")
        self.assertEqual(self.host.message("WM_RBUTTONDOWN"), 0)
        self.host.comctl32.DefSubclassProc.assert_called_once()
        self.assertEqual(self.scope["_dispatch_depth"], 0)

    def test_enumeration_failure_does_not_escape_callback(self):
        self.host.user32.GetClassNameW.side_effect = RuntimeError("enumeration failure")
        self.assertTrue(self.scope["_find_zbrush_window"](Host.HWND, 0))

    def test_edit_transition_invalidates_cache(self):
        self.host.values[EDIT] = False
        self.host.tick()
        self.assertFalse(self.host.values[CAMERA])
        self.host.values[EDIT] = True
        self.host.tick()
        self.assertTrue(self.host.values[CAMERA])

    def test_right_event_reads_edit_without_waiting_for_timer(self):
        self.host.values[EDIT] = False
        self.host.message("WM_RBUTTONDOWN")
        self.assertFalse(self.scope["_edit_mode"])
        self.assertFalse(self.host.values[CAMERA])

    def test_unreadable_edit_is_not_treated_as_off(self):
        self.host.zbc.get.side_effect = RuntimeError("unreadable")
        self.host.events.clear()
        self.host.tick()
        self.assertTrue(self.scope["_edit_mode"])
        self.assertTrue(self.host.values[CAMERA])
        self.assertEqual(self.host.events, [])

    def test_partial_setter_failure_does_not_toggle_again(self):
        def partially_set(path, value):
            self.host.set_control(path, value)
            raise RuntimeError("failed after applying value")

        self.host.zbc.set.side_effect = partially_set
        self.scope["_camera_state"] = None
        self.scope["_set_camera"](False)
        self.assertFalse(self.host.values[CAMERA])
        self.host.zbc.toggle.assert_not_called()

    def test_failed_camera_write_is_retried(self):
        self.host.values[CAMERA] = False
        self.scope["_camera_state"] = None
        self.host.zbc.set.side_effect = RuntimeError("set failed")
        self.host.zbc.toggle.side_effect = RuntimeError("toggle failed")
        self.host.tick()
        self.assertIsNone(self.scope["_camera_state"])
        self.host.zbc.set.side_effect = self.host.set_control
        self.host.zbc.toggle.side_effect = self.host.toggle_control
        self.host.tick()
        self.assertTrue(self.host.values[CAMERA])

    def test_missing_control_does_not_trigger_a_blind_toggle(self):
        del self.host.values[CAMERA]
        self.assertFalse(self.scope["_set_switch"](CAMERA, True))
        self.host.zbc.toggle.assert_not_called()

    def test_capture_loss_waits_until_button_release(self):
        self.host.message("WM_RBUTTONDOWN")
        self.host.physical_keys[2] = 0x8000
        self.host.message("WM_CAPTURECHANGED", lparam=200)
        self.host.tick()
        self.assertFalse(self.host.values[CAMERA])
        self.assertTrue(self.scope["_right_down"])
        self.host.physical_keys[2] = 0
        self.host.tick()
        self.assertTrue(self.host.values[CAMERA])
        self.assertFalse(self.scope["_right_down"])
        self.assertFalse(self.scope["_capture_lost"])

    def test_capture_recovery_respects_swapped_mouse_buttons(self):
        self.host.swapped = True
        self.host.message("WM_RBUTTONDOWN")
        self.host.physical_keys[1] = 0x8000
        self.host.message("WM_CAPTURECHANGED", lparam=200)
        self.host.tick()
        self.assertFalse(self.host.values[CAMERA])
        self.host.user32.GetAsyncKeyState.assert_called_with(1)
        self.host.physical_keys[1] = 0
        self.host.tick()
        self.assertTrue(self.host.values[CAMERA])

    def test_native_capture_loss_and_nested_timer_do_not_relock_mid_up(self):
        self.host.message("WM_RBUTTONDOWN")
        observed = []

        def native(message):
            if message == self.scope["WM_RBUTTONUP"]:
                self.host.message("WM_CAPTURECHANGED", lparam=0)
                self.host.tick()
                observed.append(self.host.values[CAMERA])

        self.host.native_handler = native
        self.host.message("WM_RBUTTONUP")
        self.assertEqual(observed, [False])
        self.assertTrue(self.host.values[CAMERA])

    def test_cancel_and_focus_loss_defer_restoration(self):
        for message in ("WM_CANCELMODE", "WM_ACTIVATEAPP"):
            with self.subTest(message=message):
                self.host.message("WM_RBUTTONDOWN")
                self.host.message(message, wparam=0)
                self.assertFalse(self.host.values[CAMERA])
                self.host.tick()
                self.assertTrue(self.host.values[CAMERA])

    def test_disable_stops_polling_and_enable_refreshes(self):
        old_id = self.scope["_edit_timer_id"]
        self.scope["_toggle"](None, False)
        self.assertFalse(self.host.values[CAMERA])
        self.assertEqual(self.host.timers, {})
        self.host.zbc.get.reset_mock()
        self.host.message("WM_TIMER", old_id)
        self.host.zbc.get.assert_not_called()
        self.scope["_toggle"](None, True)
        self.assertTrue(self.host.values[CAMERA])
        self.assertEqual(len(self.host.timers), 1)

    def test_idle_ticks_do_not_repeat_writes_or_poll_mouse(self):
        self.host.zbc.set.reset_mock()
        self.host.user32.GetAsyncKeyState.reset_mock()
        for _ in range(25):
            self.host.tick()
        self.host.zbc.set.assert_not_called()
        self.host.user32.GetAsyncKeyState.assert_not_called()

    def test_repeated_enable_disable_keeps_one_timer_and_stops_cleanly(self):
        for cycle in range(100):
            with self.subTest(cycle=cycle):
                self.scope["_toggle"](None, False)
                self.assertEqual(self.host.timers, {})
                self.assertEqual(self.scope["_edit_timer_id"], 0)
                self.scope["_toggle"](None, True)
                self.assertEqual(len(self.host.timers), 1)
                self.assertEqual(len(self.host.hooks), 1)
                self.assertTrue(self.host.values[CAMERA])
        self.scope["_toggle"](None, False)
        self.assertEqual(self.host.timers, {})
        self.assertEqual(self.scope["_edit_timer_id"], 0)
        self.assertFalse(self.host.values[CAMERA])

    def test_own_timer_is_consumed_even_when_refresh_raises(self):
        with mock.patch.dict(self.scope, {"_refresh_edit_mode": mock.Mock(side_effect=RuntimeError("tick"))}):
            self.assertEqual(self.host.tick(), 0)
        self.host.comctl32.DefSubclassProc.assert_not_called()

    def test_foreign_timer_is_forwarded(self):
        self.assertEqual(self.host.message("WM_TIMER", self.scope["_edit_timer_id"] + 1), 321)
        self.host.comctl32.DefSubclassProc.assert_called_once()

    def test_destroy_clears_state_even_if_native_removal_fails(self):
        self.host.kill_ok = False
        self.host.remove_ok = False
        self.host.zbc.set.reset_mock()
        self.host.message("WM_NCDESTROY")
        self.assertEqual(self.scope["_hwnd"], 0)
        self.assertEqual(self.scope["_edit_timer_id"], 0)
        self.assertFalse(self.scope["_hook_installed"])
        self.assertFalse(self.scope["_enabled"])
        self.assertTrue(self.scope["_shutdown"]())
        self.host.zbc.set.assert_not_called()

    def test_destroy_during_native_up_skips_host_postprocessing(self):
        self.host.message("WM_RBUTTONDOWN")

        def native(message):
            if message == self.scope["WM_RBUTTONUP"]:
                self.host.message("WM_NCDESTROY")

        self.host.native_handler = native
        self.host.zbc.set.reset_mock()
        self.host.message("WM_RBUTTONUP")
        self.host.zbc.set.assert_not_called()
        self.assertEqual(self.scope["_dispatch_depth"], 0)

    def test_reload_same_globals_detaches_old_callback_first(self):
        old_callback = self.scope["_subclass"]
        self.host.events.clear()
        self.host.load()
        self.assertIsNot(old_callback, self.scope["_subclass"])
        self.assertEqual(len(self.host.hooks), 1)
        self.assertEqual(len(self.host.timers), 1)
        remove_index = next(i for i, event in enumerate(self.host.events) if event[0] == "remove")
        install_index = next(i for i, event in enumerate(self.host.events) if event[0] == "install")
        self.assertLess(remove_index, install_index)
        self.assertIs(self.host.zbc._no_left_click_rotation_runtime["callback"], self.scope["_subclass"])

    def test_reload_with_new_globals_detaches_old_callback(self):
        old_callback = self.scope["_subclass"]
        self.scope = self.host.load(same_globals=False)
        self.assertEqual(len(self.host.hooks), 1)
        self.assertIsNot(old_callback, self.scope["_subclass"])
        self.assertEqual(len(self.host.timers), 1)

    def test_failed_hook_removal_aborts_reload_and_preserves_reference(self):
        runtime = self.host.zbc._no_left_click_rotation_runtime
        callback = self.scope["_subclass"]
        self.host.remove_ok = False
        with self.assertRaisesRegex(RuntimeError, "Could not detach"):
            self.host.load()
        self.assertIs(self.host.zbc._no_left_click_rotation_runtime, runtime)
        self.assertIs(runtime["callback"], callback)
        self.assertTrue(self.scope["_hook_installed"])
        self.assertEqual(len(self.host.hooks), 1)

    def test_failed_timer_removal_keeps_hook_and_callback(self):
        runtime = self.host.zbc._no_left_click_rotation_runtime
        self.host.kill_ok = False
        self.host.comctl32.RemoveWindowSubclass.reset_mock()
        self.assertFalse(self.scope["_shutdown"]())
        self.host.comctl32.RemoveWindowSubclass.assert_not_called()
        self.assertIs(self.host.zbc._no_left_click_rotation_runtime, runtime)
        self.assertEqual(len(self.host.timers), 1)

    def test_shutdown_is_rejected_during_native_dispatch(self):
        results = []
        self.host.native_handler = lambda message: results.append(self.scope["_shutdown"]())
        self.host.message(0x0400)
        self.assertEqual(results, [False])
        self.assertTrue(self.scope["_hook_installed"])

    def test_shutdown_from_other_thread_does_not_touch_resources(self):
        self.host.current_thread = 8
        self.host.user32.KillTimer.reset_mock()
        self.host.comctl32.RemoveWindowSubclass.reset_mock()
        self.assertFalse(self.scope["_shutdown"]())
        self.host.user32.KillTimer.assert_not_called()
        self.host.comctl32.RemoveWindowSubclass.assert_not_called()

    def test_cross_thread_install_is_rejected(self):
        self.assertTrue(self.scope["_shutdown"]())
        self.host.owner_thread = 8
        self.host.comctl32.SetWindowSubclass.reset_mock()
        self.host.load()
        self.host.comctl32.SetWindowSubclass.assert_not_called()
        self.assertFalse(self.scope["_enabled"])
        self.assertEqual(self.host.timers, {})

    def test_timer_start_failure_disables_and_removes_hook(self):
        self.assertTrue(self.scope["_shutdown"]())
        self.host.timer_ok = False
        self.host.load()
        self.assertFalse(self.scope["_enabled"])
        self.assertFalse(self.host.values[CAMERA])
        self.assertEqual(self.host.hooks, {})
        self.assertEqual(self.host.timers, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
