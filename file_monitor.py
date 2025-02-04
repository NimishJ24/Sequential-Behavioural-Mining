import os
import time
import platform
import subprocess
import psutil
import sqlite3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt6.QtWidgets import QInputDialog, QWidget
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from threading import Lock
import pyotp

# Define SQLite Database Path
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "activity.sqlite")


def get_locked_files():
    """Fetch locked files from the SQLite database."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM blocked_items")
        locked_files = [row[0] for row in cursor.fetchall()]
    return locked_files


class FileAccessMonitor(FileSystemEventHandler):
    def __init__(self, locked_files, update_signal, auth_key):
        super().__init__()
        self.locked_files = locked_files
        self.update_signal = update_signal  # Signal to update UI
        self.auth_key = auth_key  # Google Authenticator key
        self.lock = Lock()  # Thread-safe lock for shared resources

    def restrict_access(self, file_path):
        """Restrict all access to the file."""
        try:
            if platform.system() == "Windows":
                subprocess.run(f'icacls "{file_path}" /deny Everyone:F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.chmod(file_path, 0o000)  # No read/write/execute permissions (Linux/macOS)
            self.update_signal.emit(f"Access Restricted: {file_path}")
        except Exception as e:
            self.update_signal.emit(f"Error restricting access to {file_path}: {e}")

    def allow_access(self, file_path):
        """Restore read/write access to the file."""
        try:
            if platform.system() == "Windows":
                subprocess.run(f'icacls "{file_path}" /grant Everyone:F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.chmod(file_path, 0o644)  # Restore read/write permissions (Linux/macOS)
            self.update_signal.emit(f"Access Granted: {file_path}")
        except Exception as e:
            self.update_signal.emit(f"Error allowing access to {file_path}: {e}")

    def is_file_open(self, file_path):
        """Check if the file is currently open by any process."""
        for process in psutil.process_iter(['pid', 'open_files']):
            try:
                for file in process.info['open_files'] or []:
                    if file.path == file_path:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def verify_otp(self, file_path):
        """Show OTP dialog and verify user input."""
        otp, ok = QInputDialog.getText(None, "OTP Required", f"Enter OTP to access {file_path}:")
        if not ok:
            return False
        totp = pyotp.TOTP(self.auth_key)
        return totp.verify(otp)

    def add_locked_file(self, file_path):
        """Add a file to the locked files list."""
        with self.lock:
            if file_path not in self.locked_files:
                self.locked_files.append(file_path)
                self.restrict_access(file_path)

    def remove_locked_file(self, file_path):
        """Remove a file from the locked files list."""
        with self.lock:
            if file_path in self.locked_files:
                self.locked_files.remove(file_path)
                self.allow_access(file_path)

    def monitor_file_access(self):
        """Continuously check if locked files are accessed."""
        for file in self.locked_files[:]:  # Use a copy of the list for thread safety
            if self.is_file_open(file):
                if not self.verify_otp(file):
                    self.restrict_access(file)
                    self.update_signal.emit(f"Access Denied: {file}")
                else:
                    self.allow_access(file)
                    self.update_signal.emit(f"Access Granted: {file}")

                    while self.is_file_open(file):
                        time.sleep(2)

                    self.restrict_access(file)
                    self.update_signal.emit(f"File Closed & Locked Again: {file}")


class FileMonitorThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, locked_files, auth_key):
        super().__init__()
        self.locked_files = locked_files
        self.auth_key = auth_key
        self.running = True
        self.monitor = FileAccessMonitor(self.locked_files, self.update_signal, self.auth_key)
        self.timer = QTimer()
        self.timer.timeout.connect(self.monitor.monitor_file_access)

    def run(self):
        """Start monitoring locked files."""
        self.timer.start(2000)  # Check every 2 seconds

    def stop(self):
        """Stop monitoring files."""
        self.timer.stop()
        self.running = False

    def add_locked_file(self, file_path):
        """Add a file to the monitor's locked files list."""
        self.monitor.add_locked_file(file_path)

    def remove_locked_file(self, file_path):
        """Remove a file from the monitor's locked files list."""
        self.monitor.remove_locked_file(file_path)


if __name__ == "__main__":
    # Example usage (for testing purposes)
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit

    class FileMonitorApp(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("File Monitor UI")
            self.setGeometry(200, 200, 400, 300)

            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)

            self.layout = QVBoxLayout()

            self.status_box = QTextEdit()
            self.status_box.setReadOnly(True)
            self.layout.addWidget(self.status_box)

            self.start_button = QPushButton("Start Monitoring")
            self.start_button.clicked.connect(self.start_monitoring)
            self.layout.addWidget(self.start_button)

            self.stop_button = QPushButton("Stop Monitoring")
            self.stop_button.setEnabled(False)
            self.stop_button.clicked.connect(self.stop_monitoring)
            self.layout.addWidget(self.stop_button)

            self.central_widget.setLayout(self.layout)

            self.file_monitor_thread = None

        def start_monitoring(self):
            """Start file monitoring in a separate thread."""
            self.locked_files = get_locked_files()  # Fetch from database dynamically

            if not self.locked_files:
                self.update_status("No files found in database.")
                return

            self.file_monitor_thread = FileMonitorThread(self.locked_files, "your_auth_key_here")
            self.file_monitor_thread.update_signal.connect(self.update_status)
            self.file_monitor_thread.start()

            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.update_status("File Monitoring Started.")

        def stop_monitoring(self):
            """Stop file monitoring."""
            if self.file_monitor_thread:
                self.file_monitor_thread.stop()
                self.file_monitor_thread.wait()

            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.update_status("File Monitoring Stopped.")

        def update_status(self, message):
            """Update status box with messages."""
            self.status_box.append(message)

        def closeEvent(self, event):
            """Stop monitoring before closing the app."""
            self.stop_monitoring()
            event.accept()

    app = QApplication([])
    window = FileMonitorApp()
    window.show()
    app.exec()