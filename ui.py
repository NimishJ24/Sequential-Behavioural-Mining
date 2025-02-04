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
    QGridLayout, QSizePolicy, QScrollArea
)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QSize, QMargins
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QLineSeries, QDateTimeAxis, QValueAxis
import activity_monitor
from file_monitor import FileMonitorThread
import json
import time
import model

# Database Path
DB_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_activity.sqlite")
TRAINING_PATH = os.path.join(os.path.expanduser("~"), "Documents", "soft_training.sqlite")
OUTPUT_PATH = os.path.join(os.path.expanduser("~"), "Documents", "output.sqlite")

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS blocked_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT
                    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS software (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT CHECK(type IN (
                            'Keyboard', 'Click', 'Scroll', 
                            'AppOpen', 'AppClosed', 'AppInFocus',
                            'PC Usage', 'ExternalDevice'
                        )),
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
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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
    QToolButton {
        background-color: #1F1F1F;
        border-radius: 8px;
        padding: 16px;
        color: #888;
        font-weight: bold;
        border: 1px solid #333;
    }
    QToolButton:checked {
        background-color: #6200EE;
        color: white;
    }
    QToolButton:checked:hover {
        background-color: #7C4DFF;
    }
"""

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth_key = self.setup_google_authenticator()
        self.start_time = time.time()
        
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
        nav_widget.setFixedWidth(150)  # Increased width to accommodate profile
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(15)

        # Add Profile Section
        profile_widget = QWidget()
        profile_widget.setStyleSheet("border-bottom: 1px solid #333; padding-bottom: 15px;")
        profile_layout = QHBoxLayout(profile_widget)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(15)

        # Profile Picture
        profile_pic = QLabel()
        profile_pic.setFixedSize(50, 50)
        profile_pic.setStyleSheet("""
            background-color: #333;
            border-radius: 25px;
            qproperty-pixmap: url('icons/user.png');
        """)
        profile_pic.setPixmap(QIcon.fromTheme("avatar-default").pixmap(40, 40))
        
        # Profile Text
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        username = QLabel("Aryan Bharuka")
        username.setStyleSheet("font-size: 14px; font-weight: 500; color: white;")
        
        email = QLabel("aryan.bharuka20@gmail.com")
        email.setStyleSheet("font-size: 12px; color: #888;")
        
        text_layout.addWidget(username)
        text_layout.addWidget(email)
        
        profile_layout.addWidget(profile_pic)
        profile_layout.addWidget(text_widget)
        
        nav_layout.addWidget(profile_widget)

        buttons = [
            ("Home", "icons/home.png"),
            ("History", "icons/history.png"),
            ("Blocked", "icons/blocked.png")
        ]

        for text, icon in buttons:
            btn = QToolButton()
            btn.setText(text)
            btn.setIcon(QIcon(icon))
            btn.setIconSize(QSize(28, 28))  # Larger icons
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setCheckable(True)
            btn.setFixedSize(100, 100)  # Larger buttons
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

        layout.addLayout(stats_layout)
        layout.addWidget(self.timeline_chart)
        self.stack.addWidget(home_page)

    def setup_history_page(self):
        self.history_page = QWidget()
        layout = QVBoxLayout(self.history_page)
        layout.setSpacing(10)

        # Filter Bar
        filter_bar = QWidget()
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(0, 0, 0, 10)
        
        self.safe_filter = QPushButton("Safe")
        self.safe_filter.setCheckable(True)
        self.safe_filter.setStyleSheet("QPushButton:checked { background-color: #4CAF50; }")
        self.safe_filter.clicked.connect(lambda: self.apply_history_filter("safe"))
        
        self.unsafe_filter = QPushButton("Unsafe")
        self.unsafe_filter.setCheckable(True)
        self.unsafe_filter.setStyleSheet("QPushButton:checked { background-color: #FF4D4D; }")
        self.unsafe_filter.clicked.connect(lambda: self.apply_history_filter("unsafe"))
        
        filter_layout.addWidget(QLabel("Filters:"))
        filter_layout.addWidget(self.safe_filter)
        filter_layout.addWidget(self.unsafe_filter)
        filter_layout.addStretch()

        # Scroll Area
        self.history_scroll_area = QScrollArea()
        self.history_scroll_area.setWidgetResizable(True)
        self.history_scroll_content = QWidget()
        self.history_scroll_layout = QVBoxLayout(self.history_scroll_content)
        self.history_scroll_layout.setSpacing(15)
        self.history_scroll_area.setWidget(self.history_scroll_content)

        layout.addWidget(filter_bar)
        layout.addWidget(self.history_scroll_area)
        self.stack.addWidget(self.history_page)

    def setup_blocked_page(self):
       
        blocked_page = QWidget()
        layout = QVBoxLayout(blocked_page)
        layout.setContentsMargins(20, 20, 20, 20)  # Uniform margins
        layout.setSpacing(15)

        # Blocked list (main content area)
        self.blocked_list = QListWidget()
        self.blocked_list.setStyleSheet("""
            QListWidget {
                background-color: #1F1F1F;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self.blocked_list.itemDoubleClicked.connect(self.remove_blocked_item)
        layout.addWidget(self.blocked_list, 1)  # Stretch factor 1 to take remaining space

        # Add Item Button (bottom section)
        add_btn = QPushButton()
        add_btn.setFixedHeight(60)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #1F1F1F;
                border: 2px dashed #555;
                border-radius: 8px;
                margin: 10px 20px;  # Horizontal margin
            }
            QPushButton:hover {
                border-color: #777;
                background-color: #1a1a1a;
            }
        """)
        add_btn.clicked.connect(self.browse_and_lock)

        # Button content layout
        btn_content = QWidget()
        btn_layout = QHBoxLayout(btn_content)
        btn_layout.setContentsMargins(20, 0, 20, 0)
        
        # Plus icon
        plus_icon = QLabel("+")
        plus_icon.setStyleSheet("""
            background-color: #6200EE;
            color: white;
            border-radius: 15px;
            min-width: 30px;
            max-width: 30px;
            min-height: 30px;
            max-height: 30px;
            font-size: 20px;
            qproperty-alignment: AlignCenter;
        """)
        
        # Text label
        add_text = QLabel("Add Item")
        add_text.setStyleSheet("font-size: 16px; color: #888;")
        
        btn_layout.addWidget(plus_icon)
        btn_layout.addWidget(add_text)
        btn_layout.addStretch()
        
        add_btn.setLayout(btn_layout)
        layout.addWidget(add_btn)

        self.stack.addWidget(blocked_page)

    def setup_notifications(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(280)
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
        usage_series = QLineSeries()
        usage_series.setName("CPU Usage")
        pen = QPen(QColor(0, 170, 255))
        pen.setWidth(3)
        usage_series.setPen(pen)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Timestamp, cpu_usage
            FROM Software 
            WHERE type = 'PC Usage'
            ORDER BY Timestamp
        """)
        
        for ts, cpu_usage in cursor.fetchall():
            try:
                timestamp_dt = datetime.fromisoformat(ts)
            except Exception as e:
                timestamp_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            timestamp_ms = timestamp_dt.timestamp() * 1000
            usage_series.append(timestamp_ms, cpu_usage)
        
        conn.close()
        
        total_duration = time.time() - self.start_time
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        self.screen_time_card.layout().itemAt(1).widget().setText(f"{hours}h {minutes}m")
        
        timeline_chart = QChart()
        timeline_chart.addSeries(usage_series)
        timeline_chart.setTitle("Activity Timeline")
        timeline_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        timeline_chart.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        timeline_chart.setPlotAreaBackgroundBrush(QBrush(QColor(40, 40, 40)))
        timeline_chart.setPlotAreaBackgroundVisible(True)
        
        axis_x = QDateTimeAxis()
        axis_x.setFormat("hh:mm")
        axis_x.setTitleText("Time")
        axis_x.setLabelsColor(QColor("white"))
        axis_x.setTitleBrush(QBrush(QColor("white")))
        axis_x.setLinePenColor(QColor("white"))
        axis_x.setGridLineColor(QColor(80, 80, 80))
        
        timeline_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("CPU Usage (%)")
        axis_y.setLabelsColor(QColor("white"))
        axis_y.setTitleBrush(QBrush(QColor("white")))
        axis_y.setLinePenColor(QColor("white"))
        axis_y.setGridLineColor(QColor(80, 80, 80))
        
        timeline_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        
        usage_series.attachAxis(axis_x)
        usage_series.attachAxis(axis_y)
        timeline_chart.setMargins(QMargins(10, 10, 10, 10))
        self.timeline_chart.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.timeline_chart.setStyleSheet("""
            QChartView {
                border-radius: 15px;
                background-color: #1e1e1e;
            }
        """)
        self.timeline_chart.setChart(timeline_chart)

    def load_initial_data(self):
        self.load_blocked_items()
        self.load_history_data()
        self.update_charts()

    def load_blocked_items(self):
        if hasattr(self, 'blocked_list'):
            self.blocked_list.clear()
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM blocked_items")
            self.blocked_list.addItems([row[0] for row in cursor.fetchall()])
            conn.close()
            self.blocked_card.layout().itemAt(1).widget().setText(str(self.blocked_list.count()))
    
    def load_history_data(self, filter_type=None):
        while self.history_scroll_layout.count():
            child = self.history_scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        conn = sqlite3.connect(OUTPUT_PATH)
        cursor = conn.cursor()
        
        query = "SELECT description, model_output, timestamp FROM output_summary"
        if filter_type == "safe":
            query += " WHERE model_output = 'True'"
        elif filter_type == "unsafe":
            query += " WHERE model_output = 'False'"
            
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        for description, model_output, timestamp in rows:
            widget = QWidget()
            widget.setMaximumHeight(150)
            widget.setMaximumWidth(750)
            widget_layout = QVBoxLayout(widget)
            widget_layout.setContentsMargins(15, 5, 15, 5)
            widget_layout.setSpacing(2)

            widget.setStyleSheet(f"""
                QWidget {{
                    border-radius: 12px;
                    padding: 10px;
                    background-color: {'#2e7d32' if model_output.lower() == 'true' else '#d32f2f'};
                    color: white;
                }}
            """)

            description_label = QLabel(description)
            description_label.setStyleSheet("font-weight: bold; font-size: 16px;")
            description_label.setWordWrap(True)
            widget_layout.addWidget(description_label)

            timestamp_label = QLabel(timestamp)
            timestamp_label.setStyleSheet("font-size: 12px; color: #cccccc;")
            timestamp_label.setWordWrap(True)
            widget_layout.addWidget(timestamp_label)

            status_text = "SAFE" if model_output.lower() == "true" else "UNSAFE"
            status_label = QLabel(status_text)
            status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget_layout.addWidget(status_label)

            self.history_scroll_layout.addWidget(widget)

    def apply_history_filter(self, filter_type):
        self.safe_filter.setChecked(filter_type == "safe")
        self.unsafe_filter.setChecked(filter_type == "unsafe")
        self.load_history_data(filter_type)

    def log_app_usage(self, app_name, duration=None):
        data = {"title": app_name}
        if duration:
            data["duration"] = duration
        self.log_software_activity("AppInFocus" if duration else "AppOpen", data)

    def log_pc_usage(self, cpu_util, mem_util):
        self.log_software_activity("PC Usage", {
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
        detector = model.IntrusionDetector()
        model_result = bool(detector.run_inference())
        print(model_result)
        if(model_result):
            return True
        else:
            print("Ollama ka RAG nahi use kar rahe")
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