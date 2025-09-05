import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading

class MemoryManager:
    def __init__(self, memory_file: str = 'memory.json'):
        self.memory_file = memory_file
        self.lock = threading.Lock()
        self.memory = self._load_memory()
        
        # Initialize default memory structure if empty
        if not self.memory:
            self.memory = {
                'preferences': {},
                'activities': [],
                'emotions': [],
                'reminders': [],
                'app_usage': {},
                'user_info': {}
            }
            self._save_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from JSON file."""
        if not os.path.exists(self.memory_file):
            return {}
            
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_memory(self):
        """Save memory to JSON file."""
        with self.lock:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
    
    def add_activity(self, activity_type: str, details: str, **kwargs):
        """Record a user activity."""
        activity = {
            'type': activity_type,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        with self.lock:
            self.memory.setdefault('activities', []).append(activity)
            # Keep only the last 1000 activities
            self.memory['activities'] = self.memory['activities'][-1000:]
            self._save_memory()
    
    def log_emotion(self, emotion: str, confidence: float, image_path: str = None):
        """Log user's emotional state."""
        emotion_data = {
            'emotion': emotion,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat(),
            'image_path': image_path
        }
        
        with self.lock:
            self.memory.setdefault('emotions', []).append(emotion_data)
            self._save_memory()
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        with self.lock:
            self.memory.setdefault('preferences', {})[key] = value
            self._save_memory()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.memory.get('preferences', {}).get(key, default)
    
    def add_reminder(self, reminder_text: str, reminder_time: datetime):
        """Add a new reminder."""
        reminder = {
            'text': reminder_text,
            'time': reminder_time.isoformat(),
            'completed': False
        }
        
        with self.lock:
            self.memory.setdefault('reminders', []).append(reminder)
            self._save_memory()
    
    def get_pending_reminders(self) -> List[Dict]:
        """Get all pending reminders."""
        now = datetime.now()
        pending = []
        
        with self.lock:
            reminders = self.memory.get('reminders', [])
            for reminder in reminders:
                if not reminder.get('completed', False):
                    reminder_time = datetime.fromisoformat(reminder['time'])
                    if reminder_time <= now:
                        pending.append(reminder)
        
        return pending
    
    def mark_reminder_completed(self, reminder_index: int):
        """Mark a reminder as completed."""
        with self.lock:
            if 0 <= reminder_index < len(self.memory.get('reminders', [])):
                self.memory['reminders'][reminder_index]['completed'] = True
                self._save_memory()
    
    def update_app_usage(self, app_name: str, duration: float = 0):
        """Update application usage statistics."""
        with self.lock:
            app_usage = self.memory.setdefault('app_usage', {})
            if app_name not in app_usage:
                app_usage[app_name] = {'count': 0, 'total_duration': 0}
            
            app_usage[app_name]['count'] += 1
            app_usage[app_name]['total_duration'] += duration
            self._save_memory()
    
    def get_daily_summary(self, date: datetime = None) -> Dict:
        """Generate a daily summary of activities and emotions."""
        if date is None:
            date = datetime.now()
            
        date_str = date.strftime('%Y-%m-%d')
        summary = {
            'date': date_str,
            'activities': [],
            'emotions': [],
            'app_usage': {},
            'reminders': []
        }
        
        with self.lock:
            # Filter activities for the given date
            for activity in self.memory.get('activities', []):
                if activity.get('timestamp', '').startswith(date_str):
                    summary['activities'].append(activity)
            
            # Filter emotions for the given date
            for emotion in self.memory.get('emotions', []):
                if emotion.get('timestamp', '').startswith(date_str):
                    summary['emotions'].append(emotion)
            
            # Get app usage for the given date
            summary['app_usage'] = self.memory.get('app_usage', {})
            
            # Get reminders for the given date
            for reminder in self.memory.get('reminders', []):
                reminder_time = datetime.fromisoformat(reminder['time'])
                if reminder_time.strftime('%Y-%m-%d') == date_str:
                    summary['reminders'].append(reminder)
        
        return summary

# Global memory manager instance
memory = MemoryManager()
