import time
import threading
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
import re
import pytz
from dateutil import parser
import pyttsx3
import pyautogui
import os

@dataclass
class Reminder:
    """Represents a single reminder."""
    id: str
    text: str
    due_time: datetime
    created_at: datetime
    completed: bool = False
    recurring: bool = False
    recurring_interval: Optional[Dict[str, int]] = None  # e.g., {'days': 1} for daily
    last_triggered: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert reminder to a dictionary for serialization."""
        return {
            'id': self.id,
            'text': self.text,
            'due_time': self.due_time.isoformat(),
            'created_at': self.created_at.isoformat(),
            'completed': self.completed,
            'recurring': self.recurring,
            'recurring_interval': self.recurring_interval,
            'last_triggered': self.last_triggered.isoformat() if self.last_triggered else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Reminder':
        """Create a Reminder from a dictionary."""
        return cls(
            id=data['id'],
            text=data['text'],
            due_time=parser.parse(data['due_time']),
            created_at=parser.parse(data['created_at']),
            completed=data.get('completed', False),
            recurring=data.get('recurring', False),
            recurring_interval=data.get('recurring_interval'),
            last_triggered=parser.parse(data['last_triggered']) if data.get('last_triggered') else None
        )
    
    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """Check if the reminder is due."""
        if self.completed:
            return False
            
        current_time = current_time or datetime.now(pytz.utc)
        return current_time >= self.due_time
    
    def mark_completed(self):
        """Mark the reminder as completed."""
        self.completed = True
        self.last_triggered = datetime.now(pytz.utc)
    
    def reschedule(self):
        """Reschedule a recurring reminder."""
        if not self.recurring or not self.recurring_interval:
            return False
            
        self.last_triggered = datetime.now(pytz.utc)
        
        # Calculate next due time based on the interval
        if 'days' in self.recurring_interval:
            self.due_time += timedelta(days=self.recurring_interval['days'])
        elif 'weeks' in self.recurring_interval:
            self.due_time += timedelta(weeks=self.recurring_interval['weeks'])
        elif 'months' in self.recurring_interval:
            # Handle month addition (approximate, as months vary in length)
            from dateutil.relativedelta import relativedelta
            self.due_time += relativedelta(months=self.recurring_interval['months'])
        
        return True

class ReminderSystem:
    def __init__(self, storage_file: str = 'reminders.json'):
        """Initialize the reminder system."""
        self.storage_file = storage_file
        self.reminders: Dict[str, Reminder] = {}
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.engine = pyttsx3.init()
        
        # Load existing reminders
        self._load_reminders()
    
    def _load_reminders(self):
        """Load reminders from the storage file."""
        if not os.path.exists(self.storage_file):
            return
            
        try:
            with open(self.storage_file, 'r') as f:
                reminders_data = json.load(f)
                with self.lock:
                    self.reminders = {
                        rid: Reminder.from_dict(data) 
                        for rid, data in reminders_data.items()
                    }
        except (json.JSONDecodeError, FileNotFoundError):
            # If file is corrupted or doesn't exist, start with empty reminders
            self.reminders = {}
    
    def _save_reminders(self):
        """Save reminders to the storage file."""
        with self.lock:
            reminders_data = {
                rid: reminder.to_dict()
                for rid, reminder in self.reminders.items()
            }
            
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.storage_file)), exist_ok=True)
        
        # Save to file
        with open(self.storage_file, 'w') as f:
            json.dump(reminders_data, f, indent=2)
    
    def add_reminder(
        self, 
        text: str, 
        due_time: datetime, 
        recurring: bool = False,
        recurring_interval: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Add a new reminder.
        
        Args:
            text: The reminder text
            due_time: When the reminder should trigger
            recurring: Whether this is a recurring reminder
            recurring_interval: For recurring reminders, the interval between occurrences
            
        Returns:
            str: The ID of the created reminder
        """
        reminder_id = str(int(time.time()))
        
        reminder = Reminder(
            id=reminder_id,
            text=text,
            due_time=due_time,
            created_at=datetime.now(pytz.utc),
            recurring=recurring,
            recurring_interval=recurring_interval
        )
        
        with self.lock:
            self.reminders[reminder_id] = reminder
        
        self._save_reminders()
        return reminder_id
    
    def remove_reminder(self, reminder_id: str) -> bool:
        """
        Remove a reminder by ID.
        
        Returns:
            bool: True if the reminder was found and removed, False otherwise
        """
        with self.lock:
            if reminder_id in self.reminders:
                del self.reminders[reminder_id]
                self._save_reminders()
                return True
        return False
    
    def mark_completed(self, reminder_id: str) -> bool:
        """
        Mark a reminder as completed.
        
        Returns:
            bool: True if the reminder was found and marked, False otherwise
        """
        with self.lock:
            if reminder_id in self.reminders:
                self.reminders[reminder_id].mark_completed()
                self._save_reminders()
                return True
        return False
    
    def get_upcoming_reminders(self, limit: int = 10) -> List[Reminder]:
        """
        Get a list of upcoming reminders, sorted by due time.
        
        Args:
            limit: Maximum number of reminders to return
            
        Returns:
            List of Reminder objects
        """
        with self.lock:
            upcoming = [r for r in self.reminders.values() if not r.completed]
            upcoming.sort(key=lambda x: x.due_time)
            return upcoming[:limit]
    
    def get_due_reminders(self) -> List[Reminder]:
        """Get all reminders that are currently due."""
        now = datetime.now(pytz.utc)
        with self.lock:
            return [r for r in self.reminders.values() if r.is_due(now)]
    
    def _notify_reminder(self, reminder: Reminder):
        """Show a notification for a due reminder."""
        try:
            # Show a popup
            pyautogui.alert(
                title=f"Reminder: {reminder.text}",
                text=f"Time: {reminder.due_time.strftime('%Y-%m-%d %H:%M')}\n{reminder.text}",
                button='OK'
            )
            
            # Speak the reminder
            self.engine.say(f"Reminder: {reminder.text}")
            self.engine.runAndWait()
            
        except Exception as e:
            print(f"Error showing reminder: {e}")
    
    def _process_reminders(self):
        """Check for due reminders and process them."""
        while self.running:
            try:
                due_reminders = self.get_due_reminders()
                
                for reminder in due_reminders:
                    # Show notification
                    self._notify_reminder(reminder)
                    
                    # Handle recurring reminders
                    if reminder.recurring:
                        reminder.reschedule()
                    else:
                        reminder.mark_completed()
                    
                    # Save changes
                    self._save_reminders()
                
                # Check every 10 seconds
                time.sleep(10)
                
            except Exception as e:
                print(f"Error in reminder processing: {e}")
                time.sleep(60)  # Wait longer if there was an error
    
    def start(self):
        """Start the reminder system in a background thread."""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._process_reminders, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the reminder system."""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def parse_reminder_text(self, text: str) -> Optional[Dict]:
        """
        Parse natural language text to extract reminder details.
        
        Examples:
            - "Remind me to call mom tomorrow at 3pm"
            - "Set a reminder for next Monday at 9am to prepare for the meeting"
            - "Remind me every day at 8am to take my medicine"
        
        Returns:
            Dict with 'text', 'due_time', 'recurring', and 'recurring_interval' keys,
            or None if parsing fails
        """
        try:
            # This is a simplified version - you might want to use a more robust NLP library
            # like spaCy or NLTK for better parsing
            
            text = text.lower()
            now = datetime.now(pytz.utc)
            due_time = None
            recurring = False
            recurring_interval = None
            
            # Check for recurring patterns
            if "every day" in text or "daily" in text:
                recurring = True
                recurring_interval = {'days': 1}
                text = text.replace("every day", "").replace("daily", "").strip()
            elif "every week" in text or "weekly" in text:
                recurring = True
                recurring_interval = {'weeks': 1}
                text = text.replace("every week", "").replace("weekly", "").strip()
            elif "every month" in text or "monthly" in text:
                recurring = True
                recurring_interval = {'months': 1}
                text = text.replace("every month", "").replace("monthly", "").strip()
            
            # Try to extract time
            time_patterns = [
                (r'(?:at|by|for) (\d{1,2})(?::(\d{2}))?\s*([ap]m)?', 0),  # 3pm, 3:30pm, 15:30
                (r'(\d{1,2})(?::(\d{2}))?\s*([ap]m)?', 1),  # 3pm, 3:30pm, 15:30 (standalone)
            ]
            
            for pattern, group in time_patterns:
                match = re.search(pattern, text)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2) or '0')
                    period = (match.group(3) or '').lower()
                    
                    # Convert to 24-hour format
                    if period == 'pm' and hour < 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0
                    
                    # Set the time
                    due_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If the time has already passed today, move to next day
                    if due_time <= now:
                        due_time += timedelta(days=1)
                    
                    # Remove the time from the reminder text
                    text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                    break
            
            # If no time specified, default to 1 hour from now
            if not due_time:
                due_time = now + timedelta(hours=1)
            
            # Clean up the reminder text
            text = re.sub(r'\b(remind me to|set a? ?reminder(?: to)?|that|to)\b', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\s+', ' ', text).strip().strip('.,!?')
            
            if not text:
                return None
            
            return {
                'text': text,
                'due_time': due_time,
                'recurring': recurring,
                'recurring_interval': recurring_interval
            }
            
        except Exception as e:
            print(f"Error parsing reminder text: {e}")
            return None
    
    def add_reminder_from_text(self, text: str) -> Optional[str]:
        """
        Add a reminder by parsing natural language text.
        
        Returns:
            str: The ID of the created reminder, or None if parsing failed
        """
        reminder_data = self.parse_reminder_text(text)
        if not reminder_data:
            return None
            
        return self.add_reminder(
            text=reminder_data['text'],
            due_time=reminder_data['due_time'],
            recurring=reminder_data['recurring'],
            recurring_interval=reminder_data['recurring_interval']
        )

# Global reminder system instance
reminder_system = ReminderSystem()
