import sys
import os
import sqlite3
import pyotp
import qrcode
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLabel, QListWidget, QStackedWidget, QMessageBox, QLineEdit,
    QInputDialog, QToolButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGridLayout, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QSize
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QLineSeries, QDateTimeAxis, QValueAxis
import activity_monitor
from file_monitor import FileMonitorThread
import json

# Database Path
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "activity.sqlite")

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS blocked_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT
                    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS Software (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        Type TEXT NOT NULL,
                        Keyboard TEXT,
                        Click TEXT,
                        Scroll TEXT,
                        AppOpen TEXT,
                        AppClosed TEXT,
                        AppInFocus TEXT,
                        AllAppsOpen TEXT,
                        PCUsage TEXT,
                        ExternalPeripherals TEXT,
                        Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )""")
    conn.commit()
    conn.close()

init_db()

# Modern Dark Theme
DARK_THEME = """
    QWidget {
        background-color: #121212;
        color: #FFFFFF;
        font-family: 'Segoe UI';
    }
    QPushButton {
        background-color: #1F1F1F;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px;
        font-size: 14px;
        min-width: 120px;
    }
    QPushButton:hover {
        background-color: #2D2D2D;
    }
    QPushButton:pressed {
        background-color: #3D3D3D;
    }
    QListWidget {
        background-color: #1F1F1F;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 8px;
    }
    QTableWidget {
        background-color: #1F1F1F;
        border: 1px solid #333;
        border-radius: 8px;
        gridline-color: #333;
    }
    QHeaderView::section {
        background-color: #2D2D2D;
        padding: 8px;
        border: none;
    }
    QToolButton {
        background-color: #6200EE;
        border-radius: 24px;
        padding: 16px;
        color: white;
        font-weight: bold;
    }
    QToolButton:hover {
        background-color: #7C4DFF;
    }
    .Card {
        background-color: #1F1F1F;
        border-radius: 12px;
        padding: 20px;
    }
    .StatLabel {
        font-size: 16px;
        color: #888;
    }
    .StatValue {
        font-size: 32px;
        font-weight: bold;
        color: #6200EE;
    }
    QChartView {
        background-color: #1F1F1F;
        border-radius: 12px;
    }
"""

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth_key = self.setup_google_authenticator()
        
        self.nav_buttons = {}
        self.locked_files = self.get_blocked_items()
        self.setup_ui()
        
        self.setup_monitoring()
        self.load_initial_data()
        
    def get_blocked_items(self):
        """Get blocked items from database (without UI interaction)"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM blocked_items")
        locked_files = [row[0] for row in cursor.fetchall()]
        conn.close()
        return locked_files

    def setup_ui(self):
        self.setWindowTitle("Activity Monitor")
        self.setGeometry(100, 100, 1280, 720)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        self.setup_navigation()
        self.setup_stack_widget()
        self.setup_notifications()
        self.setStyleSheet(DARK_THEME)

    def setup_navigation(self):
        nav_widget = QWidget()
        nav_widget.setFixedWidth(100)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(10)

        buttons = [
            ("Home", "icons/home.png"),
            ("History", "icons/history.png"),
            ("Blocked", "icons/blocked.png")
        ]

        for text, icon in buttons:
            btn = QToolButton()
            btn.setText(text)
            btn.setIcon(QIcon(icon))
            btn.setIconSize(QSize(24, 24))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            btn.setFixedSize(80, 80)
            btn.clicked.connect(self.change_page)
            nav_layout.addWidget(btn)
            self.nav_buttons[text] = btn

        nav_layout.addStretch()
        self.main_layout.addWidget(nav_widget)

    def setup_stack_widget(self):
        self.stack = QStackedWidget()
        self.setup_home_page()
        self.setup_history_page()
        self.setup_blocked_page()
        self.main_layout.addWidget(self.stack, 3)

    def setup_home_page(self):
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Stats Cards
        stats_layout = QGridLayout()
        self.screen_time_card = self.create_stat_card("Screen Time", "0h 0m")
        self.activities_card = self.create_stat_card("Activities", "0")
        self.blocked_card = self.create_stat_card("Blocked Items", str(len(self.locked_files)))
        
        stats_layout.addWidget(self.screen_time_card, 0, 0)
        stats_layout.addWidget(self.activities_card, 0, 1)
        stats_layout.addWidget(self.blocked_card, 0, 2)

        # Charts
        self.timeline_chart = QChartView()
        self.timeline_chart.setMinimumHeight(300)
        self.distribution_chart = QChartView()
        self.distribution_chart.setMinimumHeight(300)

        layout.addLayout(stats_layout)
        layout.addWidget(self.timeline_chart)
        layout.addWidget(self.distribution_chart)
        self.stack.addWidget(home_page)

    def setup_history_page(self):
        history_page = QWidget()
        layout = QVBoxLayout(history_page)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Type", "Details", "Timestamp", "CPU Tick"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().hide()
        self.history_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.history_table)
        self.stack.addWidget(history_page)

    def setup_blocked_page(self):
        blocked_page = QWidget()
        layout = QVBoxLayout(blocked_page)
        layout.setSpacing(15)
        
        # Initialize blocked_list here
        self.blocked_list = QListWidget()  # Add this line
        self.blocked_list.itemDoubleClicked.connect(self.remove_blocked_item)
        
        add_btn = QToolButton()
        add_btn.setText("Add Item")
        add_btn.setIcon(QIcon("icons/add.png"))
        add_btn.clicked.connect(self.browse_and_lock)
        
        layout.addWidget(add_btn)
        layout.addWidget(self.blocked_list)
        self.stack.addWidget(blocked_page)

    def setup_notifications(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(300)
        layout = QVBoxLayout(sidebar)
        title = QLabel("Notifications")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        
        self.notification_panel = QListWidget()
        self.notification_panel.setStyleSheet("""
            QListWidget::item {
                padding: 12px;
                border-radius: 8px;
                margin: 4px;
                background-color: #1F1F1F;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(self.notification_panel)
        self.main_layout.addWidget(sidebar)

    def create_stat_card(self, title, value):
        card = QWidget()
        card.setStyleSheet(".Card {background-color: #1F1F1F; border-radius: 12px;}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel(title)
        label.setStyleSheet(".StatLabel {font-size: 16px; color: #888;}")
        value_label = QLabel(value)
        value_label.setStyleSheet(".StatValue {font-size: 32px; font-weight: bold; color: #6200EE;}")
        
        layout.addWidget(label)
        layout.addWidget(value_label)
        return card

    def update_charts(self):
        # Timeline Chart
        usage_series = QLineSeries()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""SELECT Timestamp, PCUsage 
                        FROM Software 
                        WHERE Type = 'PCUsage'
                        ORDER BY Timestamp""")
        
        for ts, pc_usage in cursor.fetchall():
            usage_data = json.loads(pc_usage)
            timestamp = datetime.fromisoformat(ts)
            usage_series.append(
                timestamp.timestamp() * 1000, 
                usage_data.get('cpu_utilization', 0)
            )
        
        timeline_series = QLineSeries()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, cpu_tick FROM activity ORDER BY timestamp")
        
        total_duration = 0
        prev_time = None
        for ts, tick in cursor.fetchall():
            current_time = datetime.fromisoformat(ts)
            int(current_time.timestamp() * 1000)
            if prev_time:
                total_duration += (current_time - prev_time).total_seconds()
            prev_time = current_time
            timeline_series.append(current_time.timestamp() * 1000, float(tick))
        
        # Update screen time
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        self.screen_time_card.layout().itemAt(1).widget().setText(f"{hours}h {minutes}m")
        
        timeline_chart = QChart()
        timeline_chart.addSeries(timeline_series)
        timeline_chart.setTitle("Activity Timeline")
        timeline_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        axis_x = QDateTimeAxis()
        axis_x.setFormat("hh:mm")
        axis_y = QValueAxis()
        timeline_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        timeline_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        timeline_series.attachAxis(axis_x)
        timeline_series.attachAxis(axis_y)
        self.timeline_chart.setChart(timeline_chart)

        # Distribution Chart
        pie_series = QPieSeries()
        cursor.execute("SELECT type, COUNT(*) FROM activity GROUP BY type")
        total_activities = 0
        for activity_type, count in cursor.fetchall():
            pie_series.append(f"{activity_type} ({count})", count)
            total_activities += count
        
        self.activities_card.layout().itemAt(1).widget().setText(str(total_activities))
        
        distribution_chart = QChart()
        distribution_chart.addSeries(pie_series)
        distribution_chart.setTitle("Activity Distribution")
        distribution_chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        self.distribution_chart.setChart(distribution_chart)
        
        conn.close()

    def load_initial_data(self):
        self.load_blocked_items()
        self.load_history_data()
        self.update_charts()

    def load_blocked_items(self):
        """Load items into the UI list"""
        if hasattr(self, 'blocked_list'):  # Safety check
            self.blocked_list.clear()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM blocked_items")
            self.blocked_list.addItems([row[0] for row in cursor.fetchall()])
            conn.close()
            self.blocked_card.layout().itemAt(1).widget().setText(str(self.blocked_list.count()))
    
    def load_history_data(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""SELECT Type, Timestamp, 
                        CASE 
                            WHEN Type = 'Keyboard' THEN Keyboard
                            WHEN Type = 'Click' THEN Click
                            WHEN Type = 'PCUsage' THEN PCUsage
                            ELSE ''
                        END AS Details
                        FROM Software
                        ORDER BY Timestamp DESC""")
        
        self.history_table.setRowCount(0)
        
        for row_idx, (act_type, timestamp, details) in enumerate(cursor.fetchall()):
            self.history_table.insertRow(row_idx)
            self.history_table.setItem(row_idx, 0, QTableWidgetItem(act_type))
            self.history_table.setItem(row_idx, 1, QTableWidgetItem(timestamp))
            
            # Format details based on type
            try:
                detail_data = json.loads(details)
                formatted = "\n".join([f"{k}: {v}" for k,v in detail_data.items()])
            except:
                formatted = details
                
            self.history_table.setItem(row_idx, 2, QTableWidgetItem(formatted))
        
        conn.close()

    def log_app_usage(self, app_name, duration=None):
        data = {"title": app_name}
        if duration:
            data["duration"] = duration
        self.log_software_activity("AppInFocus" if duration else "AppOpen", data)

    def log_pc_usage(self, cpu_util, mem_util):
        self.log_software_activity("PCUsage", {
            "cpu_utilization": cpu_util,
            "memory_utilization": mem_util
        })

    def change_page(self):
        btn = self.sender()
        page_name = btn.text()
        
        for button in self.nav_buttons.values():
            button.setChecked(False)
        btn.setChecked(True)
        
        if page_name == "Home":
            self.update_charts()
        elif page_name == "History":
            if not self.verify_authenticator():
                QMessageBox.warning(self, "Access Denied", "Invalid OTP!")
                return
            self.load_history_data()
        
        self.stack.setCurrentIndex(list(self.nav_buttons.keys()).index(page_name))

    def setup_monitoring(self):
        self.monitor_thread = activity_monitor.ActivityMonitor()
        self.monitor_thread.log_signal.connect(self.update_notifications)
        self.monitor_thread.start()
        
        self.file_monitor_thread = FileMonitorThread(self.locked_files, self.verify_authenticator)
        self.file_monitor_thread.update_signal.connect(self.update_notifications)
        self.file_monitor_thread.start()

    def update_notifications(self, message):
        self.notification_panel.insertItem(0, message)
        self.update_charts()
        self.load_blocked_items()

    def setup_google_authenticator(self):
        key_path = os.path.join(os.path.expanduser("~"), "Documents", "auth_key.txt")
        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                return f.read().strip()

        new_key = pyotp.random_base32()
        totp_uri = pyotp.TOTP(new_key).provisioning_uri(name="ActivityMonitor", issuer_name="SecureApp")
        
        qr = qrcode.make(totp_uri)
        qr_label = QLabel()
        qr_label.setPixmap(QPixmap.fromImage(qr.toqimage()))
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Scan QR Code")
        msg_box.setText("Scan with Google Authenticator:")
        msg_box.setIconPixmap(qr_label.pixmap())
        msg_box.exec()
        
        while True:
            otp, ok = QInputDialog.getText(self, "Authentication", "Enter OTP:")
            if not ok:
                sys.exit()
            if pyotp.TOTP(new_key).verify(otp):
                with open(key_path, "w") as f:
                    f.write(new_key)
                return new_key
            QMessageBox.warning(self, "Invalid OTP", "Please try again")

    def verify_authenticator(self):
        totp = pyotp.TOTP(self.auth_key)
        otp, ok = QInputDialog.getText(self, "Authentication", "Enter OTP:", QLineEdit.EchoMode.Password)
        return ok and totp.verify(otp)

    def browse_and_lock(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File to Lock")
        if path and self.verify_authenticator():
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blocked_items (name) VALUES (?)", (path,))
            conn.commit()
            conn.close()
            self.update_notifications(f"File locked: {path}")
            self.file_monitor_thread.monitor.restrict_access(path)

    def remove_blocked_item(self, item):
        if self.verify_authenticator():
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM blocked_items WHERE name = ?", (item.text(),))
            conn.commit()
            conn.close()
            self.update_notifications(f"File unlocked: {item.text()}")
            self.file_monitor_thread.monitor.allow_access(item.text())

    def closeEvent(self, event):
        self.monitor_thread.stop()
        self.file_monitor_thread.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainUI()
    window.show()
    sys.exit(app.exec())