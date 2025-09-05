import time
import threading
import pygetwindow as gw
import pyautogui
# pytesseract removed to avoid dependency issues
from PIL import ImageGrab
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os
import json
from dataclasses import dataclass, asdict

# OCR functionality disabled to avoid tesseract dependency

@dataclass
class WindowInfo:
    title: str
    app_name: str
    timestamp: str
    screenshot_path: str = ""
    extracted_text: str = ""
    duration: float = 0.0

class ActivityMonitor:
    def __init__(self, capture_interval: float = 5.0, save_screenshots: bool = False, 
                 save_dir: str = 'activity_data'):
        """
        Initialize the activity monitor.
        
        Args:
            capture_interval: How often to capture window info (in seconds)
            save_screenshots: Whether to save screenshots of active windows
            save_dir: Directory to save screenshots and activity data
        """
        self.capture_interval = capture_interval
        self.save_screenshots = save_screenshots
        self.save_dir = save_dir
        self.is_running = False
        self.activities: List[WindowInfo] = []
        self.lock = threading.Lock()
        self.current_window = None
        self.window_start_time = time.time()
        
        # Create save directory if it doesn't exist
        if save_screenshots and not os.path.exists(save_dir):
            os.makedirs(save_dir)
    
    def _get_active_window_info(self) -> Optional[Tuple[str, str]]:
        """Get information about the currently active window."""
        try:
            window = gw.getActiveWindow()
            if window and window.title:
                return window.title, window.process.name() if hasattr(window, 'process') else "Unknown"
        except Exception as e:
            print(f"Error getting window info: {e}")
        return None, None
    
    def _capture_window_screenshot(self, window_title: str) -> str:
        """Capture a screenshot of the active window."""
        if not self.save_screenshots:
            return ""
            
        try:
            # Get the window
            window = gw.getWindowsWithTitle(window_title)
            if not window:
                return ""
                
            window = window[0]
            
            # Bring window to front to capture it
            window.activate()
            time.sleep(0.2)  # Give it time to come to front
            
            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(self.save_dir, f"screenshot_{timestamp}.png")
            
            # Get window position and size
            left, top, width, height = window.left, window.top, window.width, window.height
            
            # Capture the screen region
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            screenshot.save(filename)
            
            return filename
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return ""
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image using OCR - DISABLED to avoid tesseract dependency."""
        # OCR functionality disabled to avoid tesseract dependency
        return ""
    
    def _process_active_window(self):
        """Process the currently active window."""
        title, app_name = self._get_active_window_info()
        if not title or not app_name:
            return
            
        current_time = time.time()
        
        # Check if window changed
        if self.current_window and (self.current_window.title != title or 
                                  self.current_window.app_name != app_name):
            # Update duration for previous window
            self.current_window.duration = current_time - self.window_start_time
            
            # Add to activities
            with self.lock:
                self.activities.append(self.current_window)
            
            # Save to file (optional)
            if self.save_screenshots:
                self._save_activity_log()
            
            # Reset for new window
            self.current_window = None
        
        # If no current window or window changed
        if not self.current_window:
            # Capture screenshot
            screenshot_path = self._capture_window_screenshot(title)
            
            # Extract text from the window
            extracted_text = self._extract_text_from_image(screenshot_path) if screenshot_path else ""
            
            # Create new window info
            self.current_window = WindowInfo(
                title=title,
                app_name=app_name,
                timestamp=datetime.now().isoformat(),
                screenshot_path=screenshot_path,
                extracted_text=extracted_text
            )
            self.window_start_time = current_time
    
    def _save_activity_log(self):
        """Save activity log to a JSON file."""
        if not self.save_screenshots or not self.activities:
            return
            
        try:
            log_file = os.path.join(self.save_dir, "activity_log.json")
            
            # Convert WindowInfo objects to dictionaries
            activities_data = [asdict(activity) for activity in self.activities]
            
            # Save to file
            with open(log_file, 'w') as f:
                json.dump(activities_data, f, indent=2)
        except Exception as e:
            print(f"Error saving activity log: {e}")
    
    def start(self):
        """Start monitoring activity in a background thread."""
        if self.is_running:
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_activity, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop monitoring activity."""
        self.is_running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join()
        
        # Save final activity log
        if self.save_screenshots:
            self._save_activity_log()
    
    def _monitor_activity(self):
        """Main monitoring loop to run in a separate thread."""
        while self.is_running:
            try:
                self._process_active_window()
            except Exception as e:
                print(f"Error in activity monitor: {e}")
            
            # Wait for the next capture interval
            time.sleep(self.capture_interval)
    
    def get_recent_activities(self, limit: int = 10) -> List[WindowInfo]:
        """Get the most recent window activities."""
        with self.lock:
            return self.activities[-limit:]
    
    def get_most_used_apps(self, limit: int = 5) -> List[Dict]:
        """Get the most used applications by duration."""
        app_usage: Dict[str, float] = {}
        
        with self.lock:
            for activity in self.activities:
                app_usage[activity.app_name] = app_usage.get(activity.app_name, 0) + activity.duration
        
        # Sort by duration (descending)
        sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
        return [{"app_name": app, "duration": duration} for app, duration in sorted_apps[:limit]]
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

# Global activity monitor instance
activity_monitor = ActivityMonitor(capture_interval=5.0, save_screenshots=True)
