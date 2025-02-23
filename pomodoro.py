import tkinter as tk
from tkinter import messagebox
import threading
import time
import simpleaudio as sa
import os

class PomodoroTimer:
    def __init__(self, master):
        self.master = master
        self.master.title("Pomodoro Timer")
        
        # Default Settings
        self.num_work_sessions = tk.IntVar(value=4)
        self.work_length_minutes = tk.IntVar(value=25)
        self.break_length_minutes = tk.IntVar(value=5)
        
        # Timer State
        self.current_session_index = 0   # Keeps track of which (work/break) session in the sequence we're on
        self.is_paused = True
        self.timer_thread = None
        self.time_remaining = 0         # Time remaining in seconds for the current session
        
        # Build UI
        self.build_config_ui()
        self.build_timer_ui()
        
        # Prepare the session sequence once "Start" is clicked
        self.session_sequence = []  # Will be a list of (duration_in_seconds, 'work'/'break')
    
    def build_config_ui(self):
        """Create the configuration area on the GUI."""
        config_frame = tk.Frame(self.master, bd=2, relief=tk.RIDGE, padx=5, pady=5)
        config_frame.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(config_frame, text="Number of Work Sessions:").grid(row=0, column=0, sticky='e')
        tk.Entry(config_frame, textvariable=self.num_work_sessions, width=5).grid(row=0, column=1, padx=5, sticky='w')
        
        tk.Label(config_frame, text="Work Session (min):").grid(row=1, column=0, sticky='e')
        tk.Entry(config_frame, textvariable=self.work_length_minutes, width=5).grid(row=1, column=1, padx=5, sticky='w')
        
        tk.Label(config_frame, text="Break (min):").grid(row=2, column=0, sticky='e')
        tk.Entry(config_frame, textvariable=self.break_length_minutes, width=5).grid(row=2, column=1, padx=5, sticky='w')
        
        start_button = tk.Button(config_frame, text="Set/Restart Pomodoro", command=self.setup_pomodoro)
        start_button.grid(row=0, column=2, rowspan=3, padx=10, pady=2)
    
    def build_timer_ui(self):
        """Create the timer display and control buttons."""
        timer_frame = tk.Frame(self.master, bd=2, relief=tk.RIDGE, padx=5, pady=5)
        timer_frame.pack(side=tk.TOP, fill=tk.X)

        self.timer_label = tk.Label(timer_frame, text="00:00", font=("Helvetica", 48))
        self.timer_label.pack(side=tk.TOP, pady=10)
        
        controls_frame = tk.Frame(timer_frame)
        controls_frame.pack(side=tk.BOTTOM, pady=5)
        
        self.pause_button = tk.Button(controls_frame, text="Start", width=10, command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=0, padx=5)
        
        backward_button = tk.Button(controls_frame, text="<< Backward", width=10, command=self.backward)
        backward_button.grid(row=0, column=1, padx=5)
        
        reset_button = tk.Button(controls_frame, text="Reset Timer", width=10, command=self.reset_current_timer)
        reset_button.grid(row=0, column=2, padx=5)
        
        forward_button = tk.Button(controls_frame, text="Forward >>", width=10, command=self.forward)
        forward_button.grid(row=0, column=3, padx=5)
    
    def setup_pomodoro(self):
        """Initialize the sequence of sessions and reset everything."""
        self.is_paused = True
        self.pause_button.config(text="Start", state=tk.NORMAL)
        
        # Create the sequence: [ (work_length_seconds, 'work'), (break_length_seconds, 'break'), ... ]
        self.session_sequence.clear()
        
        total_work_sessions = self.num_work_sessions.get()
        work_secs = self.work_length_minutes.get() * 60
        break_secs = self.break_length_minutes.get() * 60
        
        for i in range(total_work_sessions):
            self.session_sequence.append((work_secs, 'work'))
            # For all but the last work session, add a break after
            if i < total_work_sessions - 1:
                self.session_sequence.append((break_secs, 'break'))
        
        self.current_session_index = 0
        self.time_remaining = self.session_sequence[self.current_session_index][0]
        
        self.update_timer_label()
    
    def toggle_pause(self):
        """Start or pause the timer."""
        if not self.session_sequence:
            messagebox.showerror("Error", "Please set up the Pomodoro timer first by clicking 'Set/Restart Pomodoro'")
            return
            
        if self.is_paused:
            self.is_paused = False
            self.pause_button.config(text="Pause")
            # Start the timer thread if not running
            if not self.timer_thread or not self.timer_thread.is_alive():
                self.timer_thread = threading.Thread(target=self.run_timer)
                self.timer_thread.daemon = True
                self.timer_thread.start()
        else:
            self.is_paused = True
            self.pause_button.config(text="Start")
    
    def run_timer(self):
        """Count down the timer in a separate thread."""
        # Whenever we "start" a work session, we should show the 'start' popup/sound
        # But only if we're in a work session and we haven't just resumed from a pause
        # If the timer was just set up or we just advanced to a new session:
        current_session_type = self.session_sequence[self.current_session_index][1]
        
        # If we are at the start (or forwarded/backed) exactly
        # and it's a work session, play start.wav and show popup
        if self.time_remaining == self.session_sequence[self.current_session_index][0]:
            if current_session_type == 'work':
                self.notify_session_start()
        
        while not self.is_paused and self.time_remaining > 0:
            time.sleep(1)
            if not self.is_paused:
                self.time_remaining -= 1
                self.update_timer_label()
        
        # If we reached 0 and are still not paused, move to the next session
        if self.time_remaining == 0 and not self.is_paused:
            # End-of-session notification if it was a 'work' session
            if current_session_type == 'work':
                self.notify_session_end()
            
            # Move to the next session if available
            self.current_session_index += 1
            if self.current_session_index < len(self.session_sequence):
                self.time_remaining = self.session_sequence[self.current_session_index][0]
                # Automatically resume the next session (if user hasn't paused)
                self.update_timer_label()
                self.run_timer()  # Recurse: start the next session
            else:
                # All sessions completed
                self.is_paused = True
                self.pause_button.config(text="Start", state=tk.DISABLED)
    
    def update_timer_label(self):
        """Format and display the remaining time (MM:SS)."""
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
    
    def forward(self):
        """Skip to the end of the current session."""
        self.time_remaining = 0  # This triggers the session to end in run_timer()
    
    def backward(self):
        """Move backward:
           - If more than 5s have elapsed in the current session, reset to its beginning.
           - Otherwise, go to the previous session's beginning (if any).
        """
        current_duration = self.session_sequence[self.current_session_index][0]
        elapsed = current_duration - self.time_remaining
        
        if elapsed > 5:
            # Reset to start of current session
            self.time_remaining = current_duration
            self.update_timer_label()
        else:
            # Move to previous session if it exists
            if self.current_session_index > 0:
                self.current_session_index -= 1
                self.time_remaining = self.session_sequence[self.current_session_index][0]
                self.update_timer_label()
    
    def reset_current_timer(self):
        """Reset the current session to its initial duration."""
        self.time_remaining = self.session_sequence[self.current_session_index][0]
        self.update_timer_label()
    
    def notify_session_start(self):
        """Show full screen popup + play 'start.wav' if it's a work session start."""
        self.show_fullscreen_popup("Work Session Started!")
        self.play_sound("sounds/start.wav")
    
    def notify_session_end(self):
        """Show full screen popup + play appropriate sound when a work session ends."""
        # Check if it is the final work session
        # We can do so by seeing if there's another work session coming up or not
        total_work_sessions = self.num_work_sessions.get()
        
        # Count how many work sessions are in the sequence up to now
        work_session_count = 0
        for idx in range(self.current_session_index + 1):
            if self.session_sequence[idx][1] == 'work':
                work_session_count += 1
        
        if work_session_count == total_work_sessions:
            # This was the final work session
            msg = "Final Work Session Completed!"
            sound_file = "sounds/final.wav"
        else:
            msg = "Work Session Ended!"
            sound_file = "sounds/end.wav"
        
        self.show_fullscreen_popup(msg)
        self.play_sound(sound_file)
    
    def show_fullscreen_popup(self, message):
        """Create a short-lived, full-screen popup with the given message."""
        popup = tk.Toplevel(self.master)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        
        # Make it cover the entire screen
        popup.geometry(f"{popup.winfo_screenwidth()}x{popup.winfo_screenheight()}+0+0")
        
        label = tk.Label(popup, text=message, font=("Helvetica", 48), fg="white", bg="black")
        label.pack(expand=True, fill="both")
        
        # Close automatically after 3 seconds
        # (Or you could require user click to dismiss)
        popup.after(3000, popup.destroy)
    
    def play_sound(self, filepath):
        """Play a WAV file using simpleaudio."""
        if os.path.exists(filepath):
            wave_obj = sa.WaveObject.from_wave_file(filepath)
            wave_obj.play()
        else:
            print(f"Sound file not found: {filepath}")

def main():
    root = tk.Tk()
    app = PomodoroTimer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
