import sys
import os
import sqlite3
import pyotp
import qrcode
import pygetwindow as gw
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QLabel, QListWidget, QStackedWidget, QMessageBox, QLineEdit, QInputDialog, QToolButton
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import activity_monitor
from file_monitor import monitor_files

# Define SQLite Database
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "activity.sqlite")

# Ensure database exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT,
                        details TEXT,
                        timestamp TEXT,
                        identification TEXT
                    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS blocked_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT
                    )""")
    conn.commit()
    conn.close()

init_db()

# Dark Theme Stylesheet
DARK_THEME = """
    QWidget { background-color: #121212; color: #ffffff; font-size: 14px; }
    QPushButton { background-color: #1f1f1f; border: 1px solid #333; padding: 8px; border-radius: 5px; }
    QPushButton:hover { background-color: #333333; }
    QListWidget { background-color: #1f1f1f; border: 1px solid #333; }
    QLabel { font-size: 16px; }
    QLineEdit { background-color: #1f1f1f; border: 1px solid #333; padding: 5px; color: white; }
"""

class FileMonitorThread(QThread):
    update_signal = pyqtSignal(str)  # Signal to update the UI

    def __init__(self, locked_files, verify_otp, parent=None):
        super().__init__(parent)
        self.locked_files = locked_files
        self.verify_otp = verify_otp

    def run(self):
        # Monitoring files
        monitor_files(self.locked_files, self.verify_otp, self.update_signal)

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth_key = self.setup_google_authenticator()
        self.setWindowTitle("Activity Monitor")
        self.setGeometry(100, 100, 900, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
    
        # Left Navbar
        self.navbar = QVBoxLayout()
        self.nav_buttons = {
            "Home": QPushButton("Home"),
            "History Log": QPushButton("History Log"),
            "Blocked Setting": QPushButton("Blocked Setting"),
            "Report": QPushButton("Report"),
            "Add People": QPushButton("Add People")
        }
        for btn in self.nav_buttons.values():
            btn.clicked.connect(self.change_page)
            self.navbar.addWidget(btn)

        # Center Stack Widget
        self.stack = QStackedWidget()
        self.pages = {
            "Home": QWidget(),
            "History Log": QWidget(),
            "Blocked Setting": QWidget(),
            "Report": QWidget(),
            "Add People": QWidget()
        }

        self.blocked_list = QListWidget()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM blocked_items")
        for row in cursor.fetchall():
            self.blocked_list.addItem(row[0])
        conn.close()

        self.browse_button = QToolButton()
        self.browse_button.setIcon(QIcon("icons/folder.png"))  # Use a folder icon
        self.browse_button.setToolTip("Browse and lock files/folders")
        self.browse_button.clicked.connect(self.browse_and_lock)

        blocked_layout = QVBoxLayout()
        blocked_layout.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignRight)
        blocked_layout.addWidget(self.blocked_list)
        self.pages["Blocked Setting"].setLayout(blocked_layout)

        self.locked_files = self.get_blocked_items()

        for page_name, page_widget in self.pages.items():
            self.stack.addWidget(page_widget)

        # Right Panel (Notification Log)
        self.notification_panel = QListWidget()

        # Layouts
        self.main_layout.addLayout(self.navbar, 1)
        self.main_layout.addWidget(self.stack, 4)
        self.main_layout.addWidget(self.notification_panel, 2)

        # Apply Dark Theme
        self.setStyleSheet(DARK_THEME)

        # Start Background Monitoring
        self.monitor_thread = activity_monitor.ActivityMonitor()
        self.monitor_thread.log_signal.connect(self.update_notifications)
        self.monitor_thread.start()

        # File monitor thread
        self.file_monitor_thread = FileMonitorThread(self.locked_files, self.verify_otp)
        self.file_monitor_thread.update_signal.connect(self.update_notifications)
        self.file_monitor_thread.start()

        # Correct the call to monitor_files with update_signal:
        # self.file_monitor_thread = FileMonitorThread(self.locked_files, self.verify_otp)
        # self.file_monitor_thread.update_signal.connect(self.update_notifications)
        # monitor_files(self.locked_files, self.verify_otp, self.update_notifications)

        # Connect double-click event to handle file removal
        self.blocked_list.itemDoubleClicked.connect(self.remove_blocked_item_on_double_click)

    def setup_google_authenticator(self):
        key_path = os.path.join(os.path.expanduser("~"), "Documents", "auth_key.txt")
        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                return f.read().strip()

        new_key = pyotp.random_base32()
        app_name = "MySecurityApp"
        issuer = "Tarush"
        totp_uri = pyotp.TOTP(new_key).provisioning_uri(name=app_name, issuer_name=issuer)

        qr = qrcode.make(totp_uri)
        qr_pixmap = QPixmap.fromImage(qr.toqimage())
        qr_label = QLabel()
        qr_label.setPixmap(qr_pixmap)
        qr_label.setScaledContents(True)

        qr_dialog = QMessageBox(self)
        qr_dialog.setWindowTitle("Scan QR Code")
        qr_dialog.setText("Scan this QR code in Google Authenticator.")
        qr_dialog.setIconPixmap(qr_pixmap)
        
        retry = True
        while retry:
            qr_dialog.exec()

            totp = pyotp.TOTP(new_key)
            otp, ok = QInputDialog.getText(self, "Google Authenticator", "Enter OTP:", QLineEdit.EchoMode.Password)

            if not ok:
                QMessageBox.warning(self, "Setup Canceled", "Google Auth setup was canceled. Exiting...")
                sys.exit(0)

            if totp.verify(otp):
                with open(key_path, "w") as f:
                    f.write(new_key)
                return new_key
            else:
                retry = QMessageBox.question(self, "Invalid OTP", "The OTP is incorrect. Try again?", 
                                              QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def start_file_monitor(self):
        self.file_monitor_thread.start()
    
    def change_page(self):
        button = self.sender()
        page_name = button.text()

        if page_name == "History Log":
            if not self.verify_authenticator():
                QMessageBox.warning(self, "Access Denied", "Invalid OTP. Access denied!")
                return

        elif page_name == "Add People":
            new_auth_key = self.setup_google_authenticator()
            QMessageBox.information(self, "User Added", "New user setup complete!")

        elif page_name == "Blocked Setting":
            # Ensure files in the blocked list require OTP verification to be removed
            blocked_items = self.get_blocked_items()  # Fetch list of locked files from the database
            
            # if blocked_items:  # If there are any blocked items
                # item_to_remove = QInputDialog.getItem(self, "Remove Blocked File", 
                #                                     "Select a file to remove:", 
                #                                     blocked_items, editable=False)
                # if item_to_remove:
                #     # Ask for OTP before removing the file
                #     if not self.verify_authenticator():
                #         QMessageBox.warning(self, "Access Denied", "Invalid OTP. Unable to remove file.")
                #         return
                #     self.remove_blocked_item(item_to_remove)
                #     QMessageBox.information(self, "File Removed", f"{item_to_remove} has been successfully removed.")

        self.stack.setCurrentWidget(self.pages[page_name])

    def verify_otp(self, auth_key):
        otp, ok = QInputDialog.getText(self, "Google Authenticator", "Enter OTP:", QLineEdit.EchoMode.Password)
        if not ok:
            return False
        totp = pyotp.TOTP(auth_key)
        return totp.verify(otp)
    
    def verify_authenticator(self):
        totp = pyotp.TOTP(self.auth_key)
        otp, ok = QInputDialog.getText(self, "Google Authenticator", "Enter OTP:", QLineEdit.EchoMode.Password)
        return ok and totp.verify(otp)

    def show_qr_code(self, qr_path):
        qr_label = QLabel(self)
        pixmap = QPixmap(qr_path)
        qr_label.setPixmap(pixmap)
        qr_label.setScaledContents(True)
        qr_label.setGeometry(100, 100, 250, 250)  # Adjust position and size
        qr_label.show()

    def update_notifications(self, message):
        self.notification_panel.addItem(message)

    def remove_blocked_item_on_double_click(self, item):
        file_path = item.text()
        
        # Ask for OTP verification
        if self.verify_authenticator():
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blocked_items WHERE name = ?", (file_path,))
            conn.commit()
            conn.close()

            # Remove the item from the list
            self.blocked_list.takeItem(self.blocked_list.row(item))
            QMessageBox.information(self, "Unlocked", f"{file_path} has been unlocked.")
        else:
            QMessageBox.warning(self, "Access Denied", "Incorrect OTP. File not unlocked.")

    def browse_and_lock(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Lock")

        if file_path:
            if self.verify_authenticator():
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO blocked_items (name) VALUES (?)", (file_path,))
                conn.commit()
                conn.close()

                self.blocked_list.addItem(file_path)
            else:
                QMessageBox.warning(self, "Access Denied", "Incorrect OTP. File not locked.")

    def get_blocked_items(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM blocked_items")
        blocked_items = [row[0] for row in cursor.fetchall()]
        conn.close()
        return blocked_items

    def closeEvent(self, event):
        self.monitor_thread.stop()
        self.file_monitor_thread.quit()
        self.file_monitor_thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainUI()
    main_window.show()
    sys.exit(app.exec())
