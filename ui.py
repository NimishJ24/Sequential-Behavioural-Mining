import sys
import os
import sqlite3
import pyotp
import time
import psutil
import json
import qrcode
import pygetwindow as gw
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QListWidget, QFileDialog, QStackedWidget, QMessageBox, QLineEdit, QInputDialog
    )
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pynput import keyboard, mouse
import activity_monitor

# Define SQLite Database
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "activity.sqlite")

# Ensure database exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            details TEXT,
            timestamp TEXT,
            identification TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocked_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)
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

    def setup_google_authenticator(self):
        key_path = os.path.join(os.path.expanduser("~"), "Documents", "auth_key.txt")

        # If already set up, return existing key
        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                return f.read().strip()

        # Generate new key
        new_key = pyotp.random_base32()

        # Generate QR Code URI
        app_name = "MySecurityApp"
        issuer = "Tarush"
        totp_uri = pyotp.TOTP(new_key).provisioning_uri(name=app_name, issuer_name=issuer)

        # Generate and Display QR Code
        qr = qrcode.make(totp_uri)
        qr_pixmap = QPixmap.fromImage(qr.toqimage())

        # Show the QR Code in a pop-up
        qr_label = QLabel()
        qr_label.setPixmap(qr_pixmap)
        qr_label.setScaledContents(True)

        qr_dialog = QMessageBox(self)
        qr_dialog.setWindowTitle("Scan QR Code")
        qr_dialog.setText("Scan this QR code in Google Authenticator.")
        qr_dialog.setIconPixmap(qr_pixmap)
        
        retry = True  # Control retry loop
        while retry:
            qr_dialog.exec()  # Show QR code popup

            # Ask user to enter OTP
            totp = pyotp.TOTP(new_key)
            otp, ok = QInputDialog.getText(self, "Google Authenticator", "Enter OTP:", QLineEdit.EchoMode.Password)

            if not ok:  # User clicked "Cancel"
                QMessageBox.warning(self, "Setup Canceled", "Google Auth setup was canceled. Exiting...")
                sys.exit(0)  # Properly exit the application

            if totp.verify(otp):  # Valid OTP
                with open(key_path, "w") as f:
                    f.write(new_key)
                return new_key
            else:
                retry = QMessageBox.question(
                    self, "Invalid OTP", "The OTP is incorrect. Try again?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes
    
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
            
        self.stack.setCurrentWidget(self.pages[page_name])

    def verify_otp(self, auth_key):
        otp, ok = QInputDialog.getText(self, "Google Authenticator", "Enter OTP:", QLineEdit.EchoMode.Password)
        if not ok:
            return False

        totp = pyotp.TOTP(auth_key)
        return totp.verify(otp)

    def show_qr_code(self, qr_path):
        qr_label = QLabel(self)
        pixmap = QPixmap(qr_path)
        qr_label.setPixmap(pixmap)
        qr_label.setScaledContents(True)
        qr_label.setGeometry(100, 100, 250, 250)  # Adjust position and size
        qr_label.show()
    
    def update_notifications(self, message):
        self.notification_panel.addItem(message)

    def closeEvent(self, event):
        self.monitor_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainUI()
    main_window.show()
    sys.exit(app.exec())
