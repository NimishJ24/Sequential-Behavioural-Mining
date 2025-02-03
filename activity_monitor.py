from PyQt5.QtCore import QThread, pyqtSignal
import os
import sqlite3
import time
from pynput import keyboard, mouse
import json
import pygetwindow as gw
import psutil  
import threading


DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "activity.sqlite")


def create_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            details TEXT,
            timestamp TEXT,
            cpu_tick REAL
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
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll,
            on_move=self.on_mouse_move
        )
        self.key_events = {} 
        self.mouse_drag_start = None 
        self.windows = {} 
        self.cpu_memory_timer = None  

    def run(self):
        self.log_open_windows() 
        self.keyboard_listener.start()
        self.mouse_listener.start()
        self.start_cpu_memory_monitor() 
        while self.running:
            self.log_apps()
            self.sleep(5)

    def log_event(self, event_type, details):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cpu_tick = time.process_time() 
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO activity (type, details, timestamp, cpu_tick) VALUES (?, ?, ?, ?)",
                        (event_type, json.dumps(details), timestamp, cpu_tick))
        conn.commit()
        conn.close()
        self.log_signal.emit(f"[{timestamp}] {event_type}: {details}")

    def on_key_press(self, key):
        key_str = str(key)
        self.key_events[key_str] = {
            "start_time": time.time(),
            "start_cpu_tick": time.process_time()
        }
        self.log_event("Key Press", {"key": key_str})

    def on_key_release(self, key):
        key_str = str(key)
        if key_str in self.key_events:
            start_time = self.key_events[key_str]["start_time"]
            start_cpu_tick = self.key_events[key_str]["start_cpu_tick"]
            duration = time.time() - start_time
            cpu_tick_duration = time.process_time() - start_cpu_tick
            self.log_event("Key Release", {
                "key": key_str,
                "duration": duration,
                "start_cpu_tick": start_cpu_tick,
                "cpu_tick_duration": cpu_tick_duration
            })
            del self.key_events[key_str]

    def on_mouse_click(self, x, y, button, pressed):
        button_str = str(button)
        if pressed:
            self.mouse_drag_start = {
                "start_time": time.time(),
                "start_cpu_tick": time.process_time(),
                "start_position": (x, y)
            }
            self.log_event("Mouse Click Start", {
                "button": button_str,
                "position": (x, y),
                "start_cpu_tick": self.mouse_drag_start["start_cpu_tick"]
            })
        else:
            if self.mouse_drag_start:
                duration = time.time() - self.mouse_drag_start["start_time"]
                cpu_tick_duration = time.process_time() - self.mouse_drag_start["start_cpu_tick"]
                self.log_event("Mouse Click End", {
                    "button": button_str,
                    "position": (x, y),
                    "duration": duration,
                    "start_cpu_tick": self.mouse_drag_start["start_cpu_tick"],
                    "cpu_tick_duration": cpu_tick_duration
                })
                self.mouse_drag_start = None

    def on_mouse_move(self, x, y):
        if self.mouse_drag_start:
            self.log_event("Mouse Drag", {
                "start_position": self.mouse_drag_start["start_position"],
                "current_position": (x, y),
                "start_cpu_tick": self.mouse_drag_start["start_cpu_tick"]
            })

    def on_mouse_scroll(self, x, y, dx, dy):
        direction = "Up" if dy > 0 else "Down"
        self.log_event("Mouse Scroll", {
            "direction": direction,
            "position": (x, y),
            "start_cpu_tick": time.process_time()
        })

    def log_apps(self):
        active_window = gw.getActiveWindow()
        if active_window:
            active_name = active_window.title
            if active_name not in self.windows:
                self.windows[active_name] = {
                    "start_time": time.time(),
                    "start_cpu_tick": time.process_time()
                }
                self.log_event("New Window Focus", {
                    "window": active_name,
                    "start_cpu_tick": self.windows[active_name]["start_cpu_tick"]
                })
            else:
                self.log_event("Window Focus", {
                    "window": active_name,
                    "start_cpu_tick": self.windows[active_name]["start_cpu_tick"]
                })

    def log_open_windows(self):
        for window in gw.getAllWindows():
            if window.title:
                self.windows[window.title] = {
                    "start_time": time.time(),
                    "start_cpu_tick": time.process_time()
                }
                self.log_event("Initial Open Window", {
                    "window": window.title,
                    "start_cpu_tick": self.windows[window.title]["start_cpu_tick"]
                })

    def start_cpu_memory_monitor(self):
        def monitor():
            while self.running:
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent
                self.log_event("CPU and Memory Usage", {
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "cpu_tick": time.process_time()
                })
                time.sleep(5)

        self.cpu_memory_timer = threading.Thread(target=monitor)
        self.cpu_memory_timer.start()

    def stop(self):
        self.running = False
        self.keyboard_listener.stop()
        self.mouse_listener.stop()
        if self.cpu_memory_timer:
            self.cpu_memory_timer.join()