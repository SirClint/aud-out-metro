import tkinter as tk
from tkinter import ttk
import threading
import pyaudio
import configparser
import os
import time
import logging
import numpy
from pydub import AudioSegment
import wave

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE = "metronome_config.ini"
CHUNK_SIZE = 1024 # Define a buffer size for PyAudio

class MetronomeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metronome")
        self.root.geometry("400x450") # Increased size for better layout
        self.root.configure(bg='#1E1E1E') # Set background to dark grey
        self.style = ttk.Style()
        self.style.theme_use('clam') # Use a modern theme

        self.bpm = tk.IntVar(value=100)
        self.is_playing = False
        self.metronome_thread = None
        self.stop_event = threading.Event() # Event to signal thread to stop
        self.p = None
        self.stream = None
        self.start_time = None # To store the start time for the stopwatch
        self.timer_job = None # To store the after job ID for the stopwatch
        self.beat_count = 0 # Initialize beat counter
        self.beat_count_var = tk.IntVar(value=0) # Thread-safe beat counter for UI
    # audio_frames / WAV output removed (was used for debugging)
        self.load_config()

        self.create_widgets()
        self.load_sound()
        self._prepare_audio_for_bpm(self.bpm.get())

    def load_config(self):
        self.config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
            if 'Settings' in self.config and 'last_bpm' in self.config['Settings']:
                try:
                    self.bpm.set(int(self.config['Settings']['last_bpm']))
                except ValueError:
                    self.bpm.set(100) # Default if config value is invalid
        else:
            self.bpm.set(100) # Default BPM

    def save_config(self):
        if 'Settings' not in self.config:
            self.config['Settings'] = {}
        self.config['Settings']['last_bpm'] = str(self.bpm.get())
        with open(CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

    def load_sound(self):
        # Fallback to a simple click sound.
        frequency = 160  # Hz
        duration = 0.05  # seconds (shorter click)
        self.samplerate = 44100  # Hz
        t = numpy.linspace(0, duration, int(duration * self.samplerate), False)
        amplitude = 0.5
        wave_data = amplitude * numpy.sin(frequency * t * 2 * numpy.pi)
        
        # Convert to 16-bit data
        self.audio_data = (numpy.array(wave_data) * 32767).astype(numpy.int16).tobytes()
        self.original_audio_segment = None # Indicate no MP3 loaded
        logging.info("Using generated tone instead of MP3.")

        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=self.samplerate,
                                      output=True,
                                      frames_per_buffer=CHUNK_SIZE)
            logging.info("PyAudio initialized and stream opened successfully.")
        except Exception as e:
            logging.error(f"Error initializing PyAudio or opening stream: {e}")
            # If PyAudio fails, disable metronome functionality
            self.is_playing = False
            self.p = None
            self.stream = None
            # Optionally, show an error message to the user via Tkinter
            tk.messagebox.showerror("Audio Error", "Could not initialize audio. Metronome functionality may be limited.")

    def _prepare_audio_for_bpm(self, bpm_val):
        # Generate a simple click sound based on BPM
        frequency = 440  # Hz (Higher frequency for a sharper sound)
        # Make the click duration a small fraction of the beat interval, e.g., 10%
        click_duration = (60.0 / bpm_val) * 0.1 # seconds
        if click_duration > 0.05: # Cap the click duration to a reasonable max
            click_duration = 0.05

        t = numpy.linspace(0, click_duration, int(click_duration * self.samplerate), False)
        amplitude = 0.5
        wave_data = amplitude * numpy.sin(frequency * t * 2 * numpy.pi)

        # Apply an exponential decay envelope
        decay_envelope = numpy.exp(-numpy.linspace(0, 5, len(wave_data))) # Exponential decay
        wave_data = wave_data * decay_envelope

        self.audio_data = (numpy.array(wave_data) * 32767).astype(numpy.int16).tobytes()
        logging.info(f"Generated click for {bpm_val} BPM with duration {click_duration:.4f}s.")

    def increase_bpm(self):
        current_bpm = self.bpm.get()
        new_bpm = current_bpm + 5
        if new_bpm <= 300: # Set a reasonable upper limit
            self.bpm.set(new_bpm)
            self._prepare_audio_for_bpm(new_bpm)
            if not self.is_playing:
                self.beat_count = 0 # Reset beat count
                self.counter_label.config(text=f"Beat: {self.beat_count}") # Update display

    def decrease_bpm(self):
        current_bpm = self.bpm.get()
        new_bpm = current_bpm - 5
        if new_bpm >= 30: # Set a reasonable lower limit
            self.bpm.set(new_bpm)
            self._prepare_audio_for_bpm(new_bpm)
            if not self.is_playing:
                self.beat_count = 0 # Reset beat count
                self.counter_label.config(text=f"Beat: {self.beat_count}") # Update display

    def update_bpm(self, event=None): # event=None to handle both direct calls and event bindings
        try:
            new_bpm = int(self.bpm_entry.get())
            if 30 <= new_bpm <= 300: # Validate BPM range
                self.bpm.set(new_bpm)
                self._prepare_audio_for_bpm(new_bpm)
                if not self.is_playing:
                    self.beat_count = 0 # Reset beat count
                    self.counter_label.config(text=f"Beat: {self.beat_count}")
            else:
                # If BPM is out of range, reset to current valid BPM
                self.bpm_entry.delete(0, tk.END)
                self.bpm_entry.insert(0, str(self.bpm.get()))
                logging.warning(f"BPM out of range (30-300). Reset to {self.bpm.get()}.")
        except ValueError:
            # If input is not a valid integer, reset to current valid BPM
            self.bpm_entry.delete(0, tk.END)
            self.bpm_entry.insert(0, str(self.bpm.get()))
            logging.warning(f"Invalid BPM input. Reset to {self.bpm.get()}.")

    def set_bpm(self, bpm_value):
        if 30 <= bpm_value <= 300:
            self.bpm.set(bpm_value)
            self._prepare_audio_for_bpm(bpm_value)
            if not self.is_playing:
                self.beat_count = 0
                self.counter_label.config(text=f"Beat: {self.beat_count}")
            logging.info(f"BPM set to {bpm_value}.")
        else:
            logging.warning(f"Attempted to set BPM out of range: {bpm_value}.")

    def create_widgets(self):
        # Modernized UI: gradient background with a centered card
        # Configure base ttk styles
        self.style.configure('TLabel', font=('Helvetica', 12), foreground='#FFFFFF')
        self.style.configure('TButton', font=('Helvetica', 10, 'bold'), padding=6)
        self.style.configure('TEntry', font=('Helvetica', 12))

        # Card style (centered container)
        self.style.configure('Card.TFrame', background='#1E1E2A')
        self.style.configure('Card.TLabel', background='#1E1E2A', foreground='#FFFFFF')

        # Canvas with gradient background
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', self._on_canvas_configure)

        # Main frame (card) which will be placed on the canvas
        self.main_frame = ttk.Frame(self.canvas, padding="20 20 20 20", style='Card.TFrame')

        # Create a window on the canvas to hold the main_frame; store id so we can re-center on resize
        # Place initially at center; _on_canvas_configure will reposition and draw gradient
        self._main_window = self.canvas.create_window(self.root.winfo_width() // 2,
                                                     self.root.winfo_height() // 2,
                                                     window=self.main_frame,
                                                     anchor='center')

        # Build UI inside the card
        bpm_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        bpm_frame.pack(pady=8)

        ttk.Label(bpm_frame, text="BPM:", style='Card.TLabel').pack(side=tk.LEFT, padx=(0, 10))
        self.bpm_entry = ttk.Entry(bpm_frame, textvariable=self.bpm, width=5, justify='center')
        self.bpm_entry.pack(side=tk.LEFT, padx=5)
        self.bpm_entry.bind("<Return>", self.update_bpm)
        self.bpm_entry.bind("<FocusOut>", self.update_bpm)

        self.minus_button = ttk.Button(bpm_frame, text="-", command=self.decrease_bpm, width=3)
        self.minus_button.pack(side=tk.LEFT, padx=(10, 5))
        self.plus_button = ttk.Button(bpm_frame, text="+", command=self.increase_bpm, width=3)
        self.plus_button.pack(side=tk.LEFT, padx=(5, 0))

        # BPM Jump Buttons
        bpm_jump_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        bpm_jump_frame.pack(pady=12)

        ttk.Button(bpm_jump_frame, text="80", command=lambda: self.set_bpm(80), width=4).pack(side=tk.LEFT, padx=5)
        ttk.Button(bpm_jump_frame, text="110", command=lambda: self.set_bpm(110), width=4).pack(side=tk.LEFT, padx=5)
        ttk.Button(bpm_jump_frame, text="140", command=lambda: self.set_bpm(140), width=4).pack(side=tk.LEFT, padx=5)

        button_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        button_frame.pack(pady=12)

        self.start_button = ttk.Button(button_frame, text="Start", command=self.start_metronome)
        self.start_button.pack(side=tk.LEFT, padx=8)
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_metronome, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)

        exit_frame = ttk.Frame(self.main_frame, style='Card.TFrame')
        exit_frame.pack(pady=6)
        exit_button = ttk.Button(exit_frame, text="Exit", command=self.on_closing)
        exit_button.pack()

        # Timer and beat counter (styled)
        self.timer_label = ttk.Label(self.main_frame, text="00:00:00", font=('Helvetica', 14, 'bold'), style='Card.TLabel')
        self.timer_label.pack(pady=8)

        self.counter_label = ttk.Label(self.main_frame, textvariable=self.beat_count_var, font=('Helvetica', 12), style='Card.TLabel')
        self.counter_label.pack(pady=4)

        # Add subtle drop shadow by creating a slightly larger rectangle behind the card (drawn during configure)

    def _on_canvas_configure(self, event):
        # Redraw gradient and recenter card on canvas resize
        width = event.width
        height = event.height
        # Draw gradient background
        self._draw_gradient(width, height)
        # Recenter the main card
        try:
            self.canvas.coords(self._main_window, width // 2, height // 2)
        except Exception:
            pass

    def _draw_gradient(self, width, height):
        # Draw a vertical gradient from deep blue to purple
        start_color = (18, 24, 48)   # RGB
        end_color = (88, 40, 120)    # RGB
        steps = max(30, height // 8)
        # Remove old gradient items
        self.canvas.delete('gradient')
        for i in range(steps):
            r = int(start_color[0] + (end_color[0] - start_color[0]) * (i / (steps - 1)))
            g = int(start_color[1] + (end_color[1] - start_color[1]) * (i / (steps - 1)))
            b = int(start_color[2] + (end_color[2] - start_color[2]) * (i / (steps - 1)))
            color = f'#{r:02x}{g:02x}{b:02x}'
            y0 = int(i * height / steps)
            y1 = int((i + 1) * height / steps)
            self.canvas.create_rectangle(0, y0, width, y1, outline='', fill=color, tags=('gradient',))


    def update_stopwatch(self):
        if self.is_playing and self.start_time:
            elapsed_time = int(time.time() - self.start_time)
            hours = elapsed_time // 3600
            minutes = (elapsed_time % 3600) // 60
            seconds = elapsed_time % 60
            self.timer_label.config(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            self.timer_job = self.root.after(1000, self.update_stopwatch) # Update every second

    def _play_metronome(self):
        while not self.stop_event.is_set():
            start_beat_time = time.perf_counter()
            bpm_val = self.bpm.get()
            interval = 60.0 / bpm_val

            if self.stream and self.stream.is_active() and not self.stop_event.is_set():
                try:
                    self.stream.write(self.audio_data)
                    logging.debug(f"Beat played. Elapsed time for audio write: {time.perf_counter() - start_beat_time:.4f}s")
                except pyaudio.PyAudioError as pa_e:
                    logging.error(f"PyAudio error writing to stream: {pa_e}")
                except Exception as e:
                    logging.error(f"General error writing to audio stream: {e}")

            elapsed_time = time.perf_counter() - start_beat_time
            sleep_time = interval - elapsed_time

            if sleep_time > 0:
                time.sleep(sleep_time)
                logging.debug(f"Slept for {sleep_time:.4f}s. Total beat time: {time.perf_counter() - start_beat_time:.4f}s")
            else:
                logging.warning(f"Metronome falling behind. Interval: {interval:.4f}s, Elapsed: {elapsed_time:.4f}s. No sleep occurred.")


            # Update beat counter (thread-safe)
            self.beat_count_var.set(self.beat_count_var.get() + 1)

    def start_metronome(self):
        if not self.is_playing:
            self.is_playing = True
            self.stop_event.clear() # Clear the stop event for a new run
            # no audio frame recording necessary
            self.metronome_thread = threading.Thread(target=self._play_metronome)
            self.metronome_thread.daemon = True # Allow the program to exit even if thread is running
            self.metronome_thread.start()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)

            # Stopwatch and Beat Count Initialization
            self.beat_count_var.set(0) # Reset counter
            self.start_time = time.time() # Start the stopwatch
            self.update_stopwatch() # Start updating the stopwatch display

            logging.info("Metronome started.")

    def stop_metronome(self):
        if self.is_playing:
            self.is_playing = False
            self.stop_event.set() # Signal the thread to stop
            if self.metronome_thread and self.metronome_thread.is_alive():
                self.metronome_thread.join(timeout=1) # Wait for the thread to finish
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

            # Stop stopwatch and keep current display
            if self.timer_job:
                self.root.after_cancel(self.timer_job)
                self.timer_job = None
            # Do not reset timer_label or beat_count_var here, they persist until start
            self.start_time = None # Clear start time, but keep display

            logging.info("Metronome stopped.")

    def on_closing(self):
        logging.info("Application closing. Stopping metronome and saving config.")
        self.stop_metronome()
        self.save_config()


        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MetronomeApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing) # Handle window close event
    try:
        root.mainloop()
    except Exception as e:
        logging.critical(f"An unhandled exception occurred in the main loop: {e}")
        app.on_closing() # Attempt to clean up resources