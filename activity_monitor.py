import os
import sqlite3
import time
import json
import threading
import sys
import subprocess
import platform

from PyQt5.QtCore import QThread, pyqtSignal
from pynput import keyboard, mouse
import psutil

# Database: soft_activity.sqlite in the user's Documents folder
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")

def create_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS software (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            title TEXT,
            key TEXT,
            key_interval REAL,
            click_type TEXT,
            click_interval REAL,
            position TEXT,
            scroll_direction TEXT,
            scroll_speed REAL,
            scroll_interval REAL,
            duration REAL,
            cpu_usage REAL,
            memory_usage REAL,
            device_id TEXT,
            device_type TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

create_table()

class ActivityMonitor(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True

        # For keyboard events: record the press timestamp
        self.key_events = {}

        # For mouse click events
        self.mouse_click_start = None

        # For scroll events: track the time of the last scroll event
        self.last_scroll_time = None

        # For window tracking
        # Dictionary of window title -> { 'open_time': float, 'focus_time': float }
        self.open_windows = {}
        self.last_focused_window = None
        self.last_focus_time = None

        # Identify OS (Windows vs. Linux)
        self.os = platform.system()  # "Windows" or "Linux" etc.

        # Listeners for keyboard and mouse
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll,
            on_move=self.on_mouse_move
        )

    def run(self):
        # Log any already open windows (platform‐dependent)
        self.log_initial_open_windows()

        # Start listeners
        self.keyboard_listener.start()
        self.mouse_listener.start()

        # Start separate threads for periodic tasks:
        cpu_thread = threading.Thread(target=self.start_cpu_memory_monitor)
        cpu_thread.start()
        apps_thread = threading.Thread(target=self.log_all_apps_open)
        apps_thread.start()

        # Main loop: check for focus changes and closed windows every 5 seconds.
        while self.running:
            self.check_window_focus_and_closed()
            time.sleep(5)

        # On exit, join threads
        cpu_thread.join()
        apps_thread.join()

    # ---------------- Database logging helper ----------------

    def log_event(self, event_type, **kwargs):
        """
        Insert a row into the software table.
        kwargs can include any of:
          title, key, key_interval, click_type, click_interval, position,
          scroll_direction, scroll_speed, scroll_interval, duration,
          cpu_usage, memory_usage, device_id, device_type
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        # Build a dictionary of columns with default None values:
        data = {
            "type": event_type,
            "title": kwargs.get("title"),
            "key": kwargs.get("key"),
            "key_interval": kwargs.get("key_interval"),
            "click_type": kwargs.get("click_type"),
            "click_interval": kwargs.get("click_interval"),
            "position": json.dumps(kwargs.get("position")) if kwargs.get("position") else None,
            "scroll_direction": kwargs.get("scroll_direction"),
            "scroll_speed": kwargs.get("scroll_speed"),
            "scroll_interval": kwargs.get("scroll_interval"),
            "duration": kwargs.get("duration"),
            "cpu_usage": kwargs.get("cpu_usage"),
            "memory_usage": kwargs.get("memory_usage"),
            "device_id": kwargs.get("device_id"),
            "device_type": kwargs.get("device_type"),
            "timestamp": timestamp
        }
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO software (
                type, title, key, key_interval, click_type, click_interval, position, 
                scroll_direction, scroll_speed, scroll_interval, duration, 
                cpu_usage, memory_usage, device_id, device_type, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["type"], data["title"], data["key"], data["key_interval"],
            data["click_type"], data["click_interval"], data["position"],
            data["scroll_direction"], data["scroll_speed"], data["scroll_interval"],
            data["duration"], data["cpu_usage"], data["memory_usage"],
            data["device_id"], data["device_type"], data["timestamp"]
        ))
        conn.commit()
        conn.close()
        self.log_signal.emit(f"[{timestamp}] {event_type}: {kwargs}")

    # ---------------- Keyboard events ----------------
    def on_key_press(self, key):
        key_str = str(key)
        # Record the time when the key was pressed
        self.key_events[key_str] = time.time()
        # (Optionally, you could log a separate key press event here.)
    
    def on_key_release(self, key):
        key_str = str(key)
        if key_str in self.key_events:
            press_time = self.key_events[key_str]
            interval = time.time() - press_time
            # Log one Keyboard event containing key and key_interval
            self.log_event("Keyboard", key=key_str, key_interval=interval)
            del self.key_events[key_str]

    # ---------------- Mouse events ----------------
    def on_mouse_click(self, x, y, button, pressed):
        button_str = str(button)
        if pressed:
            self.mouse_click_start = time.time()
        else:
            if self.mouse_click_start:
                interval = time.time() - self.mouse_click_start
                self.log_event("Click", click_type=button_str, click_interval=interval, position=(x, y))
                self.mouse_click_start = None

    def on_mouse_move(self, x, y):
        # In this design, we log dragging only if a click is in progress.
        if self.mouse_click_start:
            # Optionally, one might log intermediate positions for a drag.
            pass

    def on_mouse_scroll(self, x, y, dx, dy):
        current_time = time.time()
        if self.last_scroll_time is None:
            scroll_interval = 0
        else:
            scroll_interval = current_time - self.last_scroll_time
        self.last_scroll_time = current_time

        direction = "Up" if dy > 0 else "Down"
        # For scroll speed, we use the magnitude of dy per second (if interval > 0)
        scroll_speed = abs(dy) / scroll_interval if scroll_interval > 0 else 0
        self.log_event("Scroll", scroll_direction=direction, scroll_speed=scroll_speed, scroll_interval=scroll_interval)

    # ---------------- Window / Application events ----------------

    def get_active_window_title(self):
        """Return the title of the active window, platform‐dependent."""
        title = None
        try:
            if self.os == "Windows":
                # Using pygetwindow on Windows
                import pygetwindow as gw
                active_window = gw.getActiveWindow()
                if active_window:
                    title = active_window.title
            elif self.os == "Linux":
                # Use xdotool to get the active window title on Linux
                result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    title = result.stdout.strip()
        except Exception as e:
            self.log_signal.emit(f"Error retrieving active window: {e}")
        return title

    def get_all_window_titles(self):
        """Return a list of titles for all open windows."""
        titles = []
        try:
            if self.os == "Windows":
                import pygetwindow as gw
                windows = gw.getAllWindows()
                titles = [w.title for w in windows if w.title]
            elif self.os == "Linux":
                # Use wmctrl to list windows on Linux
                result = subprocess.run(['wmctrl', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    # wmctrl -l returns lines like:
                    # 0x01200003  0 hostname window_title
                    for line in result.stdout.splitlines():
                        parts = line.split(None, 3)
                        if len(parts) == 4:
                            titles.append(parts[3])
        except Exception as e:
            self.log_signal.emit(f"Error retrieving all windows: {e}")
        return titles

    def log_initial_open_windows(self):
        """Log events for all currently open windows as App Open events."""
        titles = self.get_all_window_titles()
        for title in titles:
            if title:
                self.open_windows[title] = {"open_time": time.time(), "focus_time": None}
                self.log_event("App Open", title=title)

    def check_window_focus_and_closed(self):
        """Detect changes in active window focus and windows that have been closed."""
        current_active = self.get_active_window_title()

        # --- Check for focus change ---
        if current_active != self.last_focused_window:
            now = time.time()
            # If a window was focused before, log its focus duration.
            if self.last_focused_window is not None and self.last_focus_time is not None:
                duration = now - self.last_focus_time
                self.log_event("App in Focus", title=self.last_focused_window, duration=duration)
            # Update focus information
            self.last_focused_window = current_active
            self.last_focus_time = now
            # For a newly focused window, if it was not already registered as open, log it as App Open.
            if current_active and current_active not in self.open_windows:
                self.open_windows[current_active] = {"open_time": now, "focus_time": now}
                self.log_event("App Open", title=current_active)

        # --- Check for closed windows ---
        current_titles = set(self.get_all_window_titles())
        previously_open = list(self.open_windows.keys())
        for title in previously_open:
            if title not in current_titles:
                open_time = self.open_windows[title]["open_time"]
                duration = time.time() - open_time
                self.log_event("App Closed", title=title, duration=duration)
                del self.open_windows[title]

    def log_all_apps_open(self):
        """Every 10 seconds, log an event that lists all open window titles."""
        while self.running:
            titles = self.get_all_window_titles()
            # You can log one event per window or one event listing all windows.
            # Here we log one event with a comma‐separated list.
            titles_str = ", ".join(titles)
            self.log_event("All Apps Open", title=titles_str)
            time.sleep(10)

    def start_cpu_memory_monitor(self):
        """Every 10 seconds, log CPU and memory usage."""
        while self.running:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            self.log_event("PC Usage", cpu_usage=cpu_usage, memory_usage=memory_usage)
            time.sleep(10)

    # ---------------- External Peripherals ----------------
    # (This is a placeholder. In a real application you might detect USB or other peripheral events.)
    def log_external_peripherals(self, device_id, device_type):
        self.log_event("External Peripherals", device_id=device_id, device_type=device_type)

    # ---------------- Stop the monitor ----------------
    def stop(self):
        self.running = False
        self.keyboard_listener.stop()
        self.mouse_listener.stop()

if __name__ == '__main__':
    # For testing purposes, run the ActivityMonitor in a console application.
    # In a full PyQt application, you would connect log_signal to a slot that updates the UI.
    monitor = ActivityMonitor()
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
        monitor.wait()
