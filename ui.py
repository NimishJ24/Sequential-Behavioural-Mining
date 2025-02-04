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
                            'PCUsage', 'ExternalDevice'
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

        layout.addLayout(stats_layout)
        layout.addWidget(self.timeline_chart)
        self.stack.addWidget(home_page)

    def setup_history_page(self):
        # Create main widget and layout for the History page.
        self.history_page = QWidget()
        layout = QVBoxLayout(self.history_page)
        layout.setSpacing(10)

        # Create a scrollable area for history record widgets.
        self.history_scroll_area = QScrollArea()
        self.history_scroll_area.setWidgetResizable(True)
        self.history_scroll_content = QWidget()
        self.history_scroll_layout = QVBoxLayout(self.history_scroll_content)
        self.history_scroll_layout.setSpacing(15)
        self.history_scroll_area.setWidget(self.history_scroll_content)

        layout.addWidget(self.history_scroll_area)

        # Add the History page to the stack.
        self.stack.addWidget(self.history_page)

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
        # Create a line series for CPU usage
        usage_series = QLineSeries()
        usage_series.setName("CPU Usage")
        # Optional: set a custom pen for a modern look
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
            timestamp_ms = timestamp_dt.timestamp() * 1000  # QDateTimeAxis expects milliseconds
            usage_series.append(timestamp_ms, cpu_usage)
        
        conn.close()
        
        # Use the system's internal time for screen time.
        total_duration = time.time() - self.start_time  # self.start_time should be set when the monitor starts
        hours = int(total_duration // 3600)
        minutes = int((total_duration % 3600) // 60)
        self.screen_time_card.layout().itemAt(1).widget().setText(f"{hours}h {minutes}m")
        
        # Create and configure the chart
        timeline_chart = QChart()
        timeline_chart.addSeries(usage_series)
        timeline_chart.setTitle("Activity Timeline")
        timeline_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        # Set dark background for the entire chart
        timeline_chart.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        # Set a darker plot area background for contrast and enable background visibility
        timeline_chart.setPlotAreaBackgroundBrush(QBrush(QColor(40, 40, 40)))
        timeline_chart.setPlotAreaBackgroundVisible(True)
        
        # Configure the X-axis as a date/time axis.
        axis_x = QDateTimeAxis()
        axis_x.setFormat("hh:mm")
        axis_x.setTitleText("Time")
        # Set axis label and line colors to white for contrast
        axis_x.setLabelsColor(QColor("white"))
        axis_x.setTitleBrush(QBrush(QColor("white")))
        axis_x.setLinePenColor(QColor("white"))
        axis_x.setGridLineColor(QColor(80, 80, 80))
        
        timeline_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        
        # Configure the Y-axis as a value axis.
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
        """
        Clear the scroll area and load all records from the output.sqlite database.
        Each record is shown as a custom widget with a maximum height.
        """
        while self.history_scroll_layout.count():
            child = self.history_scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        conn = sqlite3.connect(OUTPUT_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT description, model_output, timestamp FROM output_summary")
        rows = cursor.fetchall()
        conn.close()
        for description, model_output, timestamp in rows:
            widget = QWidget()
            widget.setMaximumHeight(150)  # Limit the widget height.
            widget.setMaximumWidth(750)
            widget_layout = QVBoxLayout(widget)
            widget_layout.setContentsMargins(15, 5, 15, 5)
            widget_layout.setSpacing(2)  # Add spacing between elements.

            # Use a different background color based on model_output.
            widget.setStyleSheet(f"""
                QWidget {{
                    border-radius: 12px;
                    padding: 10px;
                    background-color: {'#2e7d32' if model_output.lower() == 'true' else '#d32f2f'};
                    color: white;
                }}
            """)

            # Description in bold with word wrap enabled.
            description_label = QLabel(description)
            description_label.setStyleSheet("font-weight: bold; font-size: 16px;")
            description_label.setWordWrap(True)
            description_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
            widget_layout.addWidget(description_label)

            # Timestamp in a smaller, lighter font with word wrap enabled.
            timestamp_label = QLabel(timestamp)
            timestamp_label.setStyleSheet("font-size: 12px; color: #cccccc;")
            timestamp_label.setWordWrap(True)
            timestamp_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
            widget_layout.addWidget(timestamp_label)

            # Model Output displayed as "SAFE" or "UNSAFE".
            status_text = "SAFE" if model_output.lower() == "true" else "UNSAFE" 
            status_label = QLabel(status_text)
            status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
            status_label.setWordWrap(True)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            widget_layout.addWidget(status_label)

            # Add the custom widget to the scrollable layout.
            self.history_scroll_layout.addWidget(widget)


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
        detector = model.IntrusionDetector()
        model_result = bool(detector.test())
        print(model_result)
        if(model_result):
            return True
        else:
            # insert popup ?
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