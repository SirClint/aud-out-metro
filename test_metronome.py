import unittest
import os
import configparser
from unittest import mock
import tempfile
import shutil
import threading
import time

# Defer importing the application until after we patch modules (tkinter, pyaudio, threading)

# Mock tkinter and pyaudio before importing MetronomeApp
mock_tk = mock.MagicMock()
mock_ttk = mock.MagicMock()
mock_pyaudio = mock.MagicMock()
mock_threading = mock.MagicMock(spec=threading)

# Mock tkinter.messagebox
mock_messagebox = mock.MagicMock()

# Patch tkinter, tkinter.ttk, pyaudio, threading, and tkinter.messagebox in the main module's scope
with mock.patch.dict('sys.modules', {
    'tkinter': mock_tk,
    'tkinter.ttk': mock_ttk,
    'pyaudio': mock_pyaudio,
    'threading': mock_threading,
    'tkinter.messagebox': mock_messagebox
}):
    # Import tkinter and ttk here so that their names refer to the mocked objects
    import tkinter as tk
    from tkinter import ttk

    # Patch tk.DISABLED, tk.NORMAL, and tk.END to return string literals
    tk.DISABLED = 'disabled'
    tk.NORMAL = 'normal'
    tk.END = 'end'

    # Now import the main module so that its imports use our mocked modules
    import importlib
    import main as _main
    MetronomeApp = _main.MetronomeApp
    CONFIG_FILE = _main.CONFIG_FILE

class TestMetronomeApp(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for config files
        self.test_dir = tempfile.mkdtemp()
        self.test_config_file = os.path.join(self.test_dir, CONFIG_FILE)

        # Patch CONFIG_FILE to point to our temporary file
        self.config_patcher = mock.patch('main.CONFIG_FILE', new=self.test_config_file)
        self.config_patcher.start()

        # Mock the root Tkinter object and its methods
        self.mock_root = mock.MagicMock()
        self.mock_root.winfo_width.return_value = 400
        self.mock_root.winfo_height.return_value = 450
        self.mock_root.after.return_value = 'timer_job_id' # Mock return for after calls

        # Create a dynamic mock for tk.IntVar
        self.mock_int_var_value = 100
        def mock_int_var_get():
            return self.mock_int_var_value
        def mock_int_var_set(value):
            self.mock_int_var_value = value

        mock_int_var_instance = mock.MagicMock()
        mock_int_var_instance.get.side_effect = mock_int_var_get
        mock_int_var_instance.set.side_effect = mock_int_var_set
        mock_tk.IntVar.return_value = mock_int_var_instance

        # Mock Tkinter widgets
        mock_ttk.Entry.return_value = mock.MagicMock()
        mock_ttk.Label.return_value = mock.MagicMock()
        mock_ttk.Button.return_value = mock.MagicMock()
        mock_tk.Canvas.return_value = mock.MagicMock()
        mock_ttk.Frame.return_value = mock.MagicMock()
        mock_ttk.Style.return_value = mock.MagicMock()

        # Mock threading.Event and its methods
        mock_event_instance = mock.MagicMock(spec=threading.Event)
        mock_event_instance.clear = mock.MagicMock()
        mock_event_instance.set = mock.MagicMock()
        # Patch main.threading.Event to return our mock instance
        self.threading_event_patcher = mock.patch('main.threading.Event', return_value=mock_event_instance)
        self.threading_event_patcher.start()

        # Mock threading.Thread to allow setting daemon status
        mock_thread_instance = mock.MagicMock(spec=threading.Thread)
        self.threading_thread_patcher = mock.patch('main.threading.Thread', return_value=mock_thread_instance)
        self.threading_thread_patcher.start()

        # Mock PyAudio objects
        mock_pyaudio.PyAudio.return_value = mock.MagicMock()
        mock_pyaudio.PyAudio.return_value.open.return_value = mock.MagicMock()
        mock_pyaudio.paInt16 = 8 # Mock the format constant

        # Mock config read/write operations
        self.mock_config_read = mock.patch.object(configparser.ConfigParser, 'read')
        self.mock_config_read_instance = self.mock_config_read.start()
        self.mock_config_write = mock.patch.object(configparser.ConfigParser, 'write')
        self.mock_config_write_instance = self.mock_config_write.start()

        # Mock MetronomeApp.load_config, MetronomeApp.load_sound, and _prepare_audio_for_bpm to prevent them from running during __init__
        with mock.patch.object(MetronomeApp, 'load_config'), \
             mock.patch.object(MetronomeApp, 'load_sound'), \
             mock.patch.object(MetronomeApp, '_prepare_audio_for_bpm'):
            # Instantiate the app with mocks
            self.app = MetronomeApp(self.mock_root)

        # Ensure self.app.bpm is our controlled mock_int_var_instance
        self.app.bpm = mock_tk.IntVar.return_value

        # Manually set samplerate for tests that might call _prepare_audio_for_bpm later
        self.app.samplerate = 44100

        # Reset mock_int_var_value for each test
        self.mock_int_var_value = 100

        # Ensure widgets are mocked correctly after create_widgets
        self.app.bpm_entry = mock_ttk.Entry.return_value
        self.app.counter_label = mock_ttk.Label.return_value
        self.app.start_button = mock_ttk.Button.return_value
        self.app.stop_button = mock_ttk.Button.return_value
        self.app.timer_label = mock_ttk.Label.return_value

        # Mock os.path.exists for config file handling
        self.mock_os_path_exists = mock.patch('main.os.path.exists')
        self.mock_os_path_exists_instance = self.mock_os_path_exists.start()

        # Create a real ConfigParser instance for self.app.config
        self.app.config = configparser.ConfigParser()
        self.app.config['Settings'] = {'last_bpm': '100'} # Default setting

    def tearDown(self):
        # Stop all patchers
        self.config_patcher.stop()
        self.mock_os_path_exists.stop()
        self.mock_config_read.stop()
        self.mock_config_write.stop()
        self.threading_event_patcher.stop()
        self.threading_thread_patcher.stop()
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_load_config_existing_file(self):
        self.mock_os_path_exists_instance.return_value = True
        # Simulate reading a config file with 120 BPM
        def mock_config_read(files):
            self.app.config.add_section('Settings')
            self.app.config.set('Settings', 'last_bpm', '120')
        self.mock_config_read_instance.side_effect = mock_config_read
        self.app.load_config()
        self.assertEqual(self.app.bpm.get(), 120)

    def test_load_config_no_file(self):
        self.mock_os_path_exists_instance.return_value = False
        self.app.load_config()
        self.assertEqual(self.app.bpm.get(), 100)  # Should default to 100

    def test_load_config_invalid_bpm(self):
        self.mock_os_path_exists_instance.return_value = True
        # Simulate reading a config file with an invalid BPM
        def mock_config_read(files):
            self.app.config.add_section('Settings')
            self.app.config.set('Settings', 'last_bpm', 'abc')
        self.mock_config_read_instance.side_effect = mock_config_read
        self.app.load_config()
        self.assertEqual(self.app.bpm.get(), 100)  # Should default to 100 on invalid value

    def test_save_config(self):
        self.app.bpm.set(150)
        self.app.save_config()
        self.mock_config_write_instance.assert_called_once()
        # Verify the content that would have been written to the file
        self.assertEqual(self.app.config['Settings']['last_bpm'], '150')

    def test_increase_bpm(self):
        self.app.bpm.set(100)
        self.app.increase_bpm()
        self.assertEqual(self.app.bpm.get(), 105)
        self.app.counter_label.config.assert_called_with(text="Beat: 0")

    def test_increase_bpm_upper_limit(self):
        # When increasing past the upper limit, BPM should cap at 300
        self.app.bpm.set(298)
        self.app.increase_bpm()
        self.assertEqual(self.app.bpm.get(), 300)

    def test_decrease_bpm(self):
        self.app.bpm.set(100)
        self.app.decrease_bpm()
        self.assertEqual(self.app.bpm.get(), 95)
        self.app.counter_label.config.assert_called_with(text="Beat: 0")

    def test_decrease_bpm_lower_limit(self):
        # When decreasing below the lower limit, BPM should floor at 30
        self.app.bpm.set(32)
        self.app.decrease_bpm()
        self.assertEqual(self.app.bpm.get(), 30)

    def test_update_bpm_valid_input(self):
        self.app.bpm_entry.get.return_value = "130"
        self.app.update_bpm()
        self.assertEqual(self.app.bpm.get(), 130)
        self.app.counter_label.config.assert_called_with(text="Beat: 0")

    def test_update_bpm_invalid_input(self):
        initial_bpm = self.app.bpm.get()
        self.app.bpm_entry.get.return_value = "invalid"
        self.app.update_bpm()
        self.assertEqual(self.app.bpm.get(), initial_bpm)  # Should remain unchanged
        self.app.bpm_entry.delete.assert_called_with(0, tk.END)
        self.app.bpm_entry.insert.assert_called_with(0, str(initial_bpm))

    def test_update_bpm_out_of_range(self):
        initial_bpm = self.app.bpm.get()
        self.app.bpm_entry.get.return_value = "20"  # Below lower limit
        self.app.update_bpm()
        self.assertEqual(self.app.bpm.get(), 30)  # Should be capped to 30
        self.app.counter_label.config.assert_called_with(text="Beat: 0")

        self.app.bpm_entry.get.return_value = "350"  # Above upper limit
        self.app.update_bpm()
        self.assertEqual(self.app.bpm.get(), 300)  # Should be capped to 300
        self.app.counter_label.config.assert_called_with(text="Beat: 0")

    def test_set_bpm_valid_input(self):
        self.app.set_bpm(160)
        self.assertEqual(self.app.bpm.get(), 160)
        self.app.counter_label.config.assert_called_with(text="Beat: 0")

    def test_set_bpm_out_of_range(self):
        self.app.set_bpm(20)  # Below lower limit
        self.assertEqual(self.app.bpm.get(), 30)  # Should floor to 30

        self.app.set_bpm(350)  # Above upper limit
        self.assertEqual(self.app.bpm.get(), 300)  # Should cap to 300

    def test_update_stopwatch_not_running(self):
        # Test that the stopwatch does nothing when not running
        self.app.is_playing = False
        self.app.update_stopwatch()
        self.app.timer_label.config.assert_not_called()
        self.assertIsNone(self.app.timer_job)

    def test_update_stopwatch_running(self):
        # Test that the stopwatch updates correctly when running
        self.app.is_playing = True
        self.app.start_time = time.time() - 3661  # 1 hour, 1 minute, 1 second
        self.app.update_stopwatch()
        self.app.timer_label.config.assert_called_with(text="01:01:01")
        self.assertEqual(self.app.timer_job, 'timer_job_id')  # Mock after() returns this

    def test_beat_count_updates(self):
        # Test that beat count updates correctly when metronome is running
        self.app.is_playing = True
        # Create an independent IntVar-like mock for the beat counter
        beat_var = mock.MagicMock()
        # backing storage
        beat_var._value = 0
        def beat_get():
            return getattr(beat_var, '_value', 0)
        def beat_set(v):
            beat_var._value = v
        beat_var.get.side_effect = beat_get
        beat_var.set.side_effect = beat_set
        self.app.beat_count_var = beat_var
        # Set stop_event to control the loop
        self.app.stop_event.is_set.side_effect = [False, True]  # Run once, then stop
        # Ensure bpm is non-zero so _play_metronome doesn't divide by zero
        self.app.bpm.set(100)
        # Simulate one beat
        self.app._play_metronome()
        self.assertEqual(self.app.beat_count_var.get(), 1)

    def test_audio_error_handling(self):
        # Test audio error handling in load_sound
        self.app.p = None  # Reset PyAudio instance
        self.app.stream = None  # Reset stream
        mock_pyaudio.PyAudio.side_effect = Exception("Audio error")
        try:
            self.app.load_sound()
            self.assertFalse(self.app.is_playing)
            self.assertIsNone(self.app.p)
            self.assertIsNone(self.app.stream)
        finally:
            # Clear side effect so other tests are not affected
            mock_pyaudio.PyAudio.side_effect = None

    def test_start_metronome(self):
        self.app.is_playing = False
        self.app.start_button = mock.MagicMock()  # Create fresh mock for start button
        self.app.stop_button = mock.MagicMock()   # Create fresh mock for stop button
        self.app.start_metronome()
        self.assertTrue(self.app.is_playing)
        self.app.stop_event.clear.assert_called_once()
        self.app.metronome_thread.start.assert_called_once()
        self.app.start_button.config.assert_called_with(state='disabled')
        self.app.stop_button.config.assert_called_with(state='normal')
        self.assertEqual(self.app.beat_count_var.get(), 0)
        self.assertIsNotNone(self.app.start_time)
        self.mock_root.after.assert_called_once_with(1000, self.app.update_stopwatch)

    def test_stop_metronome(self):
        self.app.is_playing = True
        self.app.timer_job = 'timer_job_id'  # Simulate an active timer job
        self.app.metronome_thread = mock.MagicMock()  # Create a mock thread
        self.app.metronome_thread.is_alive.return_value = True
        # Ensure buttons are fresh mocks so we can assert state changes
        self.app.start_button = mock.MagicMock()
        self.app.stop_button = mock.MagicMock()
        self.app.stop_metronome()
        self.assertFalse(self.app.is_playing)
        self.app.stop_event.set.assert_called_once()
        self.app.metronome_thread.join.assert_called_once_with(timeout=1)
        self.app.start_button.config.assert_called_with(state='normal')
        self.app.stop_button.config.assert_called_with(state='disabled')
        self.mock_root.after_cancel.assert_called_once_with('timer_job_id')
        self.assertIsNone(self.app.timer_job)
        self.assertIsNone(self.app.start_time)

    def test_on_closing(self):
        self.app.stream = mock.MagicMock()
        self.app.p = mock.MagicMock()
        self.app.on_closing()
        self.app.stream.stop_stream.assert_called_once()
        self.app.stream.close.assert_called_once()
        self.app.p.terminate.assert_called_once()
        self.mock_root.destroy.assert_called_once()

if __name__ == '__main__':
    unittest.main()