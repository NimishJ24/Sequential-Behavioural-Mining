import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox

class FileAccessMonitor(FileSystemEventHandler):
    def __init__(self, locked_files, verify_otp_callback, update_signal):
        self.locked_files = locked_files  # List of locked file paths
        self.verify_otp_callback = verify_otp_callback  # Function to verify OTP
        self.update_signal = update_signal  # Signal to update the UI with messages

    def on_modified(self, event):
        if event.src_path in self.locked_files:
            # Trigger OTP verification when file is modified/opened
            if not self.verify_otp_callback():
                self.update_signal.emit(f"Access Denied to {event.src_path} due to invalid OTP!")
                QMessageBox.warning(None, "Access Denied", "Invalid OTP. Access denied!")
                os.rename(event.src_path, event.src_path + "_locked")  # Renaming to prevent access
                return
            else:
                # Restore the file back to its original state
                os.rename(event.src_path + "_locked", event.src_path)


class FileMonitorThread(QThread):
    update_signal = pyqtSignal(str)  # Signal to update the UI with messages

    def __init__(self, locked_files, verify_otp_callback):
        super().__init__()
        self.locked_files = locked_files
        self.verify_otp_callback = verify_otp_callback

    def run(self):
        monitor_files(self.locked_files, self.verify_otp_callback, self.update_signal)


def start_file_monitor(locked_files, verify_otp_callback, update_signal):
    event_handler = FileAccessMonitor(locked_files, verify_otp_callback, update_signal)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(locked_files[0]), recursive=False)
    observer.start()
    return observer


def monitor_files(locked_files, verify_otp_callback, update_signal):
    # Start the file monitoring
    observer = start_file_monitor(locked_files, verify_otp_callback, update_signal)

    # Run the observer in the background
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

