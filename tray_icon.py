import sys
import os
import threading
import time
from datetime import datetime
import webbrowser
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QVBoxLayout, QLabel, QWidget, QDialog, QPushButton
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, QSize
import pyautogui

# Import our modules
from memory_manager import memory
from emotion_detector import emotion_detector
from activity_monitor import activity_monitor
from reminder_system import reminder_system

class SummaryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis Daily Summary")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        scroll = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.addWidget(self.summary_label)
        scroll_layout.addStretch()
        scroll.setLayout(scroll_layout)
        
        layout.addWidget(scroll)
        
        # Add close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate a summary of today's activities and emotions."""
        # Get today's data from memory
        today = datetime.now().strftime("%Y-%m-%d")
        activities = []
        emotions = []
        
        # Get activities and emotions from memory
        for activity in memory.memory.get('activities', []):
            if activity.get('timestamp', '').startswith(today):
                activities.append(activity)
        
        for emotion in memory.memory.get('emotions', []):
            if emotion.get('timestamp', '').startswith(today):
                emotions.append(emotion)
        
        # Generate summary text
        summary = f"<h2>Daily Summary for {today}</h2>"
        
        # Activity summary
        summary += "<h3>📊 Activity Summary</h3>"
        if activities:
            # Count activities by type
            activity_counts = {}
            for activity in activities:
                activity_type = activity.get('type', 'unknown')
                activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
            
            summary += "<p><b>Activities today:</b></p><ul>"
            for activity_type, count in activity_counts.items():
                summary += f"<li>{activity_type}: {count} times</li>"
            summary += "</ul>"
        else:
            summary += "<p>No activities recorded today.</p>"
        
        # Emotion summary
        summary += "<h3>😊 Emotion Summary</h3>"
        if emotions:
            # Calculate average emotion
            emotion_scores = {}
            for emotion in emotions:
                emotion_name = emotion.get('emotion', 'neutral')
                confidence = emotion.get('confidence', 0)
                if emotion_name in emotion_scores:
                    emotion_scores[emotion_name]['total'] += confidence
                    emotion_scores[emotion_name]['count'] += 1
                else:
                    emotion_scores[emotion_name] = {'total': confidence, 'count': 1}
            
            # Calculate average confidence for each emotion
            avg_emotions = {}
            for emotion, data in emotion_scores.items():
                avg_emotions[emotion] = data['total'] / data['count']
            
            # Get dominant emotion
            dominant_emotion = max(avg_emotions.items(), key=lambda x: x[1]) if avg_emotions else (None, 0)
            
            summary += f"<p><b>Dominant emotion today:</b> {dominant_emotion[0].capitalize()} "
            summary += f"({dominant_emotion[1]*100:.1f}% confidence)</p>"
            
            summary += "<p><b>Emotion breakdown:</b></p><ul>"
            for emotion, score in sorted(avg_emotions.items(), key=lambda x: x[1], reverse=True):
                summary += f"<li>{emotion.capitalize()}: {score*100:.1f}%</li>"
            summary += "</ul>"
        else:
            summary += "<p>No emotion data recorded today.</p>"
        
        # App usage summary
        summary += "<h3>💻 Application Usage</h3>"
        app_usage = memory.memory.get('app_usage', {})
        if app_usage:
            # Sort apps by total duration
            sorted_apps = sorted(
                app_usage.items(), 
                key=lambda x: x[1]['total_duration'], 
                reverse=True
            )[:5]  # Top 5 apps
            
            summary += "<p><b>Most used applications:</b></p><ol>"
            for app, data in sorted_apps:
                hours = data['total_duration'] / 3600  # Convert seconds to hours
                summary += f"<li>{app}: {hours:.1f} hours ({data['count']} sessions)</li>"
            summary += "</ol>"
        else:
            summary += "<p>No application usage data available.</p>"
        
        # Reminders summary
        pending_reminders = [r for r in reminder_system.reminders.values() if not r.completed]
        if pending_reminders:
            summary += "<h3>⏰ Upcoming Reminders</h3><ul>"
            for reminder in sorted(pending_reminders, key=lambda x: x.due_time)[:5]:  # Next 5 reminders
                time_str = reminder.due_time.strftime('%Y-%m-%d %H:%M')
                summary += f"<li>{time_str}: {reminder.text}</li>"
            summary += "</ul>"
        
        self.summary_label.setText(summary)

class JarvisTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        # Initialize with a default icon (will be replaced with the actual icon)
        icon = QIcon("icon.png")  # Fallback icon
        super().__init__(icon, parent)
        
        # Set up the system tray icon
        self.setToolTip("Jarvis AI Assistant")
        
        # Create the menu
        self.menu = QMenu(parent)
        
        # Add actions to the menu
        self.show_summary_action = QAction("Show Daily Summary", self)
        self.show_summary_action.triggered.connect(self.show_summary)
        
        self.reminders_action = QAction("Manage Reminders", self)
        self.reminders_action.triggered.connect(self.show_reminders)
        
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.show_settings)
        
        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(QApplication.quit)
        
        # Add actions to menu
        self.menu.addAction(self.show_summary_action)
        self.menu.addSeparator()
        self.menu.addAction(self.reminders_action)
        self.menu.addAction(self.settings_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        
        # Set the context menu
        self.setContextMenu(self.menu)
        
        # Connect the activated signal (click/double-click)
        self.activated.connect(self.on_tray_activated)
        
        # Timer for checking for notifications
        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self.check_notifications)
        self.notification_timer.start(30000)  # Check every 30 seconds
        
        # Last notification time to prevent duplicates
        self.last_notification_time = {}
    
    def show_summary(self):
        """Show the daily summary dialog."""
        self.summary_dialog = SummaryDialog()
        self.summary_dialog.exec_()
    
    def show_reminders(self):
        """Show the reminders management dialog."""
        # This would open a dialog to manage reminders
        # For now, just show a message
        self.showMessage("Jarvis", "Reminders management will be available in the next update.")
    
    def show_settings(self):
        """Show the settings dialog."""
        # This would open a settings dialog
        # For now, just show a message
        self.showMessage("Jarvis", "Settings will be available in the next update.")
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation (click/double-click)."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_summary()
    
    def check_notifications(self):
        """Check for notifications to show in the system tray."""
        try:
            # Check for due reminders
            due_reminders = reminder_system.get_due_reminders()
            for reminder in due_reminders:
                # Skip if we've already shown this notification recently
                if reminder.id in self.last_notification_time:
                    time_since_last = time.time() - self.last_notification_time[reminder.id]
                    if time_since_last < 300:  # 5 minutes
                        continue
                
                # Show notification
                self.showMessage(
                    "⏰ Reminder", 
                    reminder.text,
                    QSystemTrayIcon.Information,
                    10000  # Show for 10 seconds
                )
                
                # Update last notification time
                self.last_notification_time[reminder.id] = time.time()
                
                # Mark as completed if not recurring
                if not reminder.recurring:
                    reminder.mark_completed()
                else:
                    # Reschedule recurring reminder
                    reminder.reschedule()
                
                # Save changes
                reminder_system._save_reminders()
                
        except Exception as e:
            print(f"Error checking notifications: {e}")

def run_tray_icon():
    """Run the system tray icon in a separate thread."""
    app = QApplication(sys.argv)
    
    # Set application info
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Jarvis AI Assistant")
    app.setApplicationDisplayName("Jarvis")
    
    # Create and show the tray icon
    tray = JarvisTrayIcon()
    tray.show()
    
    # Show welcome message
    tray.showMessage("Jarvis", "Jarvis is running in the background. Right-click the tray icon for options.")
    
    # Start the application event loop
    sys.exit(app.exec_())

# Start the tray icon in a separate thread
def start_tray_icon():
    tray_thread = threading.Thread(target=run_tray_icon, daemon=True)
    tray_thread.start()
    return tray_thread

# This allows running the tray icon directly for testing
if __name__ == "__main__":
    run_tray_icon()
