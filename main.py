import speech_recognition as sr
import webbrowser
import pyttsx3
from gtts import gTTS
import pygame
import os
import subprocess
import time
import datetime
import pyjokes
import wikipedia
import wolframalpha
import pyautogui
import screen_brightness_control as sbc
from threading import Thread, Timer, Lock
from langdetect import detect
import random
import openai
import requests
import toml
import speedtest
import pywhatkit
import numpy as np
# Defer heavy imports to improve startup time
# from transformers import AutoProcessor, AutoModelForCausalLM
# import torch
import pygetwindow as gw
import pytz
from dateutil import parser
import signal
import sys

# Pygame mixer will be initialized when needed

# Import our custom modules
import automation
from memory_manager import memory
from emotion_detector import emotion_detector
from activity_monitor import activity_monitor
from reminder_system import reminder_system
from tray_icon import start_tray_icon

tray_thread = start_tray_icon()

# Load configuration from TOML file
def load_config():
    try:
        with open('config.toml', 'r') as f:
            config = toml.load(f)
            return config
    except FileNotFoundError:
        print("Error: config.toml file not found.")
        print("Please create a config.toml file with your API keys.")
        exit(1)
    except Exception as e:
        print(f"Error loading config: {e}")
        exit(1)

config = load_config()

# Model selection: 'openai' or 'ollama'
MODEL_PROVIDER = config.get('settings', {}).get('model_provider', 'openai')
OLLAMA_MODEL = config.get('settings', {}).get('ollama_model', 'llama3')

# Initialize speech engine
engine = pyttsx3.init()
recognizer = sr.Recognizer()

# Global variables
conversation_history = []
user_activity = []
activity_lock = Lock()  # For thread-safe access to user_activity
shutdown_flag = False  # Global shutdown flag for clean exit

# Initialize components are already set from imports above

# Debug mode - set to True to enable text input as fallback
DEBUG_MODE = False

# Restore ElevenLabs config and variables
openai.api_key = config['openai']['api_key']
ELEVENLABS_API_KEY = config['elevenlabs']['api_key']
ELEVENLABS_VOICE_ID = config['elevenlabs']['voice_id']

# Add TogetherAI API config
TOGETHERAI_API_KEY = config['togetherai']['api_key']
TOGETHERAI_MODEL = config['togetherai']['model']

# Global pause flag
PAUSE_FLAG = False
# Pause/resume command synonyms
PAUSE_COMMANDS = ["pause", "stop", "jarvis stop"]
RESUME_COMMANDS = ["resume", "continue", "unpause", "jarvis resume"]
# You can say: pause, stop, jarvis stop, resume, continue, unpause, jarvis resume

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    global shutdown_flag
    print("\n\nReceived interrupt signal. Shutting down gracefully...")
    shutdown_flag = True
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
if hasattr(signal, 'SIGBREAK'):  # Windows Ctrl+Break
    signal.signal(signal.SIGBREAK, signal_handler)

# gTTS speech synthesis (primary), pyttsx3 fallback
def speak(text, lang='en'):
    """Speak the given text using gTTS and pygame."""
    print(f"Speaking: {text}")
    
    try:
        # Log this interaction
        memory.add_activity('speech', f'Spoke: {text[:100]}...')
        
        # Generate speech with gTTS
        tts = gTTS(text=text, lang=lang, slow=False)
        temp_file = 'temp_speech.mp3'
        tts.save(temp_file)

        # Initialize Pygame mixer
        pygame.mixer.init()
        
        # Load and play the MP3 file
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()

        # Wait for the audio to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
    except Exception as e:
        print(f"Error in speak function: {e}")
        
    finally:
        # Cleanup
        if 'temp_file' in locals() and os.path.exists(temp_file):
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                os.remove(temp_file)
            except Exception as e:
                print(f"Error during cleanup: {e}")
            tts.save(temp_file)
            
            try:
                pygame.mixer.music.load(temp_file)
                pygame.mixer.music.play()
                
                # Add timeout to prevent hanging
                timeout_start = time.time()
                timeout_duration = 30  # 30 seconds timeout
                
                while pygame.mixer.music.get_busy():
                    if time.time() - timeout_start > timeout_duration:
                        print("Warning: Audio playback timed out, forcing stop")
                        break
                    pygame.time.Clock().tick(10)
                
                # Properly stop and wait for music to finish
                pygame.mixer.music.stop()
                # Give pygame time to fully stop and release file handle
                time.sleep(1.0)
            finally:
                # Ensure cleanup happens even if there's an error
                cleanup_attempts = 3
                cleanup_delay = 0.5
                
                for attempt in range(cleanup_attempts):
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        break  # Success, exit the loop
                    except PermissionError:
                        if attempt < cleanup_attempts - 1:  # Not the last attempt
                            print(f"Warning: Could not delete {temp_file} (file in use), retrying in {cleanup_delay}s...")
                            time.sleep(cleanup_delay)
                            cleanup_delay *= 2  # Exponential backoff
                        else:
                            print(f"Warning: {temp_file} will need manual cleanup")
                    except Exception as e:
                        print(f"Warning: Error during cleanup: {e}")
                        break
                    except Exception as e:
                        print(f"gTTS error: {e}")
            # Ultimate fallback to pyttsx3
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e2:
                print(f"pyttsx3 error: {e2}")
            except Exception as e:
                print(f"Speech error: {e}")

# Language detection
def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

def internet_speed_test():
    if PAUSE_FLAG:
        speak("Internet speed test paused, sir.")
        return
    speak("Checking internet speed sir. This may take a moment.")
    st = speedtest.Speedtest()
    download = st.download() / 1_000_000  # Convert to Mbps
    upload = st.upload() / 1_000_000      # Convert to Mbps
    speak(f"Download speed is {download:.2f} Mbps and upload speed is {upload:.2f} Mbps sir")

def play_on_youtube(query):
    speak(f"Playing {query} on YouTube sir")
    pywhatkit.playonyt(query)

def wolfram_query(query):
    try:
        res = wolframalpha.Client(config['wolframalpha']['app_id']).query(query)
        answer = next(res.results).text
        speak(f"According to Wolfram Alpha: {answer}")
    except Exception as e:
        speak("Sorry sir, I couldn't get an answer from Wolfram Alpha")

def set_alarm(hours, minutes):
    global PAUSE_FLAG
    alarm_time = f"{hours:02d}:{minutes:02d}"
    speak(f"Alarm set for {alarm_time} sir")
    while True:
        if PAUSE_FLAG:
            speak("Alarm paused, sir.")
            return
        now = datetime.datetime.now().strftime("%H:%M")
        if now == alarm_time:
            speak("Wake up sir! Alarm time!")
            break
        time.sleep(30)

# Wake word response
def wake_word_response():
    responses = [
        "At your service, sir!",
        "How may I assist you today?",
        "Yes sir, I'm listening.",
        "Jarvis here, ready to help."
    ]
    speak(random.choice(responses))

# Greet user based on time
def greet_user():
    current_hour = datetime.datetime.now().hour
    if current_hour < 12:
        greeting = "Good morning sir! How may I be of service today?"
    elif 12 <= current_hour < 18:
        greeting = "Good afternoon sir! What would you like me to do?"
    else:
        greeting = "Good evening sir! How can I assist you tonight?"
    return greeting

# Tell a joke
def tell_joke():
    joke = pyjokes.get_joke()
    print(joke)
    return joke

# Set a reminder
def set_reminder(time_in_seconds, reminder_text):
    def reminder_callback():
        if PAUSE_FLAG:
            speak("Reminder paused, sir.")
            return
        speak(f"Reminder sir: {reminder_text}")
        print(f"Reminder: {reminder_text}")
    Timer(time_in_seconds, reminder_callback).start()

# Web search
def search_web(query):
    speak(f"Searching for '{query}' sir...")
    webbrowser.open(f"https://www.google.com/search?q={query}")

# AI processing and classification with TogetherAI API
def ai_process(command):
    """
    Handles both command classification and conversation using TogetherAI API.
    If the input is classified as a 'command', returns 'command'.
    If 'conversation', returns the model-generated response.
    """
    # Classify input as command or conversation
    prompt = (
        "Classify the following user input as either a 'command' (if it is an actionable instruction for a virtual assistant, e.g., open YouTube, set a reminder, etc.) "
        "or 'conversation' (if it is a general question, chat, or not a direct command).\n"
        f"User input: {command}\n"
        "Respond with only one word: 'command' or 'conversation'."
    )
    headers = {
        "Authorization": f"Bearer {TOGETHERAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": TOGETHERAI_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 5,
        "temperature": 0
    }
    try:
        response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            classification = result["choices"][0]["message"]["content"].strip().lower()
        else:
            classification = "command"
    except Exception as e:
        print(f"TogetherAI classification error: {e}")
        classification = "command"

    if classification == "command":
        return "command"
    else:
        # Now get the conversation response from TogetherAI
        conversation_history.append({"role": "user", "content": command})
        messages = [
            {"role": "system", "content": "You are Jarvis, an advanced AI assistant. Respond formally but helpfully."},
            *conversation_history
        ]
        data = {
            "model": TOGETHERAI_MODEL,
            "messages": messages,
            "max_tokens": 256,
            "temperature": 0.7
        }
        try:
            response = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"]
            else:
                answer = "Sorry, I couldn't get a response from TogetherAI."
            conversation_history.append({"role": "assistant", "content": answer})
            if len(conversation_history) > config.get('max_history', 10):
                conversation_history[:] = conversation_history[-config.get('max_history', 10):]
            return answer
        except Exception as e:
            print(f"TogetherAI processing error: {e}")
            return "I'm having some trouble processing that request right now, sir."

# Get user input
def get_input(prompt):
    """Get user input through speech recognition with improved error handling."""
    global shutdown_flag
    
    if shutdown_flag:
        return ""
        
    speak(prompt)
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts and not shutdown_flag:
        try:
            # Check shutdown flag before each attempt
            if shutdown_flag:
                return ""
                
            with sr.Microphone() as source:
                print("\nListening for your command...")
                
                # Quick ambient noise adjustment
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                except KeyboardInterrupt:
                    print("\nInterrupted during noise calibration")
                    shutdown_flag = True
                    return ""
                
                try:
                    # Listen for the first phrase and extract it into audio data
                    print("Speak now...")
                    audio = recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=5
                    )
                    
                    # Check shutdown flag before processing
                    if shutdown_flag:
                        return ""
                    
                    # Recognize speech using Google Web Speech API
                    print("Processing your command...")
                    text = recognizer.recognize_google(audio, language="en-US").lower()
                    print(f"You said: {text}")
                    return text
                    
                except sr.WaitTimeoutError:
                    print("No speech detected. Please try again.")
                    if not shutdown_flag:
                        speak("I didn't catch that. Could you please repeat?")
                    
                except sr.UnknownValueError:
                    print("Could not understand audio. Please try again.")
                    if not shutdown_flag:
                        speak("I didn't understand that. Could you please repeat?")
                    
                except sr.RequestError as e:
                    print(f"Could not request results; {e}")
                    if not shutdown_flag:
                        speak("I'm having trouble connecting to the speech service.")
                    break
                    
                except KeyboardInterrupt:
                    print("\nSpeech recognition interrupted")
                    shutdown_flag = True
                    return ""
                    
        except KeyboardInterrupt:
            print("\nInput interrupted by user")
            shutdown_flag = True
            return ""
        except Exception as e:
            print(f"An error occurred: {e}")
            if not shutdown_flag:
                speak("Sorry, I encountered an error. Please try again.")
            
        attempt += 1
        if attempt < max_attempts and not shutdown_flag:
            print(f"Attempt {attempt + 1} of {max_attempts}...")
    
    if not shutdown_flag:
        print("Maximum attempts reached. Please try again later.")
    return ""
# Replace their usages with automation.system_control, automation.take_screenshot, etc.

def process_command(command):
    """Process the given command and return a response."""
    command = command.lower()
    response = ""
    
    # Log the command
    memory.add_activity('command', f'User command: {command}')
    
    # Check for pause/resume commands
    global PAUSE_FLAG
    if any(cmd in command for cmd in PAUSE_COMMANDS):
        PAUSE_FLAG = True
        memory.add_activity('system', 'Paused command processing')
        return "I'll pause for now. Say 'resume' when you need me."
    
    if any(cmd in command for cmd in RESUME_COMMANDS):
        PAUSE_FLAG = False
        memory.add_activity('system', 'Resumed command processing')
        return "I'm back! How can I help you?"
    
    # If we're paused, only listen for resume commands
    if PAUSE_FLAG:
        return ""
        
    # Add to conversation history
    conversation_history.append(("user", command))
    if len(conversation_history) > 10:  # Keep last 10 messages
        conversation_history.pop(0)
    
    # Check for emotion detection
    current_emotion = None
    if emotion_detector:
        current_emotion = emotion_detector.get_current_emotion()
        if current_emotion:
            memory.log_emotion(
                current_emotion.emotion, 
                current_emotion.confidence,
                current_emotion.image_path
            )
    
    # Simple command processing
    if "hello" in command or "hi" in command or "hey" in command:
        response = greet_user()
    
    elif "how are you" in command:
        # Respond based on user's emotion if available
        if current_emotion and current_emotion.confidence > 0.6:
            if current_emotion.emotion in ['happy', 'surprise']:
                response = "I'm doing great, thanks for asking! You seem to be in a good mood!"
            elif current_emotion.emotion in ['sad', 'angry']:
                response = "I'm here to help. Is there something bothering you?"
            else:
                response = "I'm functioning normally. How about you?"
        else:
            responses = ["I'm doing well, thank you!", 
                        "I'm great, thanks for asking!",
                        "I'm functioning within normal parameters."]
            response = random.choice(responses)
    
    elif "your name" in command:
        response = "I am Jarvis, your AI assistant."
    
    elif "time" in command:
        now = datetime.datetime.now()
        response = f"The current time is {now.strftime('%I:%M %p')}."
    
    elif "date" in command:
        now = datetime.datetime.now()
        response = f"Today is {now.strftime('%A, %B %d, %Y')}."
    
    elif "joke" in command:
        response = tell_joke()
    
    # Enhanced reminder system with natural language processing
    elif "remind me" in command or "set a reminder" in command:
        if reminder_system:
            reminder_id = reminder_system.add_reminder_from_text(command)
            if reminder_id:
                # Get the reminder details to confirm
                reminder = reminder_system.reminders.get(reminder_id)
                if reminder:
                    time_str = reminder.due_time.strftime('%I:%M %p on %A, %B %d')
                    freq = ""
                    if reminder.recurring and reminder.recurring_interval:
                        if 'days' in reminder.recurring_interval:
                            if reminder.recurring_interval['days'] == 1:
                                freq = " every day"
                            else:
                                freq = f" every {reminder.recurring_interval['days']} days"
                        elif 'weeks' in reminder.recurring_interval:
                            if reminder.recurring_interval['weeks'] == 1:
                                freq = " every week"
                            else:
                                freq = f" every {reminder.recurring_interval['weeks']} weeks"
                        elif 'months' in reminder.recurring_interval:
                            if reminder.recurring_interval['months'] == 1:
                                freq = " every month"
                            else:
                                freq = f" every {reminder.recurring_interval['months']} months"
                    
                    response = f"I'll remind you to {reminder.text}{freq} at {time_str}."
                else:
                    response = "I've set a reminder for you."
                
                memory.add_activity('reminder', f'Set reminder: {reminder.text} at {time_str}')
            else:
                response = "I couldn't understand the reminder details. Please try again."
        else:
            response = "Reminder system is not available."
    
    # View reminders
    elif "what are my reminders" in command or "list my reminders" in command:
        if reminder_system:
            reminders = reminder_system.get_upcoming_reminders()
            if reminders:
                response = "Here are your upcoming reminders:\n"
                for i, reminder in enumerate(reminders, 1):
                    time_str = reminder.due_time.strftime('%I:%M %p on %A, %B %d')
                    response += f"{i}. {reminder.text} at {time_str}\n"
                response = response.strip()
            else:
                response = "You don't have any upcoming reminders."
        else:
            response = "Reminder system is not available."
    
    # System controls
    elif any(cmd in command for cmd in ["volume up", "increase volume"]):
        automation.volume_up()
        response = "Volume increased."
        memory.add_activity('system', 'Increased volume')
    
    elif any(cmd in command for cmd in ["volume down", "decrease volume"]):
        automation.volume_down()
        response = "Volume decreased."
        memory.add_activity('system', 'Decreased volume')
    
    elif "mute" in command or "unmute" in command:
        automation.toggle_mute()
        response = "Volume muted." if automation.is_muted() else "Volume unmuted."
        memory.add_activity('system', 'Toggled mute')
    
    elif any(cmd in command for cmd in ["brightness up", "increase brightness"]):
        automation.increase_brightness()
        response = "Brightness increased."
        memory.add_activity('system', 'Increased brightness')
    
    elif any(cmd in command for cmd in ["brightness down", "decrease brightness"]):
        automation.decrease_brightness()
        response = "Brightness decreased."
        memory.add_activity('system', 'Decreased brightness')
    
    elif "take a screenshot" in command or "take screenshot" in command:
        try:
            screenshot_path = automation.take_screenshot()
            response = f"Screenshot saved as {screenshot_path}"
            memory.add_activity('system', f'Took screenshot: {screenshot_path}')
        except Exception as e:
            response = f"Failed to take screenshot: {str(e)}"
    
    elif "lock computer" in command or "lock the computer" in command:
        automation.lock_computer()
        response = "Locking computer."
        memory.add_activity('system', 'Locked computer')
    
    elif "sleep" in command or "go to sleep" in command:
        automation.put_to_sleep()
        response = "Putting the computer to sleep."
        memory.add_activity('system', 'Put computer to sleep')
    
    elif "shut down" in command or "shutdown" in command:
        automation.shutdown()
        response = "Shutting down the computer."
        memory.add_activity('system', 'Shut down computer')
    
    # Web and app controls
    elif "open " in command:
        app_name = command.split("open ", 1)[1].strip()
        if automation.open_application(app_name):
            response = f"Opening {app_name}."
            memory.add_activity('app', f'Opened application: {app_name}')
        else:
            response = f"I couldn't find an application named {app_name}."
    
    elif "search for" in command and "youtube" in command:
        query = command.split("search for")[1].replace("on youtube", "").strip()
        automation.search_youtube(query)
        response = f"Searching YouTube for {query}."
        memory.add_activity('web', f'Searched YouTube for: {query}')
    
    elif "search for" in command or "look up" in command:
        query = command.split("search for")[-1].split("look up")[-1].strip()
        automation.search_web(query)
        response = f"Searching the web for {query}."
        memory.add_activity('web', f'Searched web for: {query}')
    
    elif "wikipedia" in command:
        query = command.split("wikipedia")[0].strip()
        try:
            summary = wikipedia.summary(query, sentences=2)
            response = f"According to Wikipedia: {summary}"
            memory.add_activity('info', f'Looked up on Wikipedia: {query}')
        except:
            response = "Sorry, I couldn't find any information on that topic."
    
    # Emotion detection
    elif "how am i feeling" in command or "what's my mood" in command:
        if current_emotion and current_emotion.confidence > 0.5:
            emotion_map = {
                'happy': 'You look happy! 😊',
                'sad': 'You seem a bit sad. Is everything okay? 😔',
                'angry': 'You look a bit angry. Would you like to talk about it? 😠',
                'surprise': 'You look surprised! 😲',
                'fear': 'You seem a bit scared. Is everything alright? 😨',
                'disgust': 'You seem disgusted by something. 😖',
                'neutral': 'You seem neutral. How are you feeling? 😐'
            }
            emotion_text = emotion_map.get(
                current_emotion.emotion, 
                f"You seem {current_emotion.emotion}."
            )
            response = f"Based on your facial expression, {emotion_text.lower()}"
        else:
            response = "I'm not sure how you're feeling. Could you tell me?"
    
    # Activity monitoring
    elif "what have i been doing" in command or "my activity" in command:
        if activity_monitor:
            recent_activities = activity_monitor.get_recent_activities(5)
            if recent_activities:
                response = "Here's what you've been up to recently:\n"
                for i, activity in enumerate(recent_activities, 1):
                    time_str = activity.timestamp.strftime('%I:%M %p')
                    response += f"{i}. {time_str} - {activity.app_name}: {activity.title}\n"
                response = response.strip()
            else:
                response = "I don't have any recent activity data yet."
        else:
            response = "Activity monitoring is not available."
    
    # If no command matched, use AI to generate a response
    if not response:
        response = ai_process(command)
    
    # Add to conversation history
    conversation_history.append(("assistant", response))
    
    # Log the interaction
    with activity_lock:
        user_activity.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "command": command,
            "response": response[:500]  # Limit response length
        })
    
    return response

# Wake word detection function
def listen_for_wake_word():
    """
    Listens for the wake word 'hey jarvis' (case-insensitive).
    Returns True if detected, False otherwise.
    """
    if shutdown_flag:
        return False
        
    try:
        with sr.Microphone() as source:
            recognizer.pause_threshold = 0.5
            recognizer.energy_threshold = 300
            
            try:
                audio = recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Check shutdown flag before processing
                if shutdown_flag:
                    return False
                
                # Process audio with timeout
                try:
                    text = recognizer.recognize_google(audio, show_all=False).lower()
                    
                    if "hey jarvis" in text or "jarvis" in text:
                        print("\nWake word detected!")
                        wake_word_response()
                        return True
                        
                except sr.UnknownValueError:
                    # Could not understand audio - this is normal
                    pass
                except sr.RequestError as e:
                    print(f"\nSpeech service error: {e}")
                    time.sleep(1)
                    
            except sr.WaitTimeoutError:
                # No speech detected - this is normal
                pass
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                print("\nInterrupted by user")
                shutdown_flag = True
                return False
            except Exception as e:
                print(f"\nWake word recognition error: {e}")
                time.sleep(0.5)
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        shutdown_flag = True
        return False
    except Exception as e:
        print(f"\nMicrophone error: {e}")
        time.sleep(0.5)
        
    return False

def get_text_input():
    """Get user input via text as a fallback when voice recognition fails."""
    try:
        command = input("\nType your command (or 'quit' to exit, 'voice' to try voice again): ").strip()
        if command.lower() in ['quit', 'exit', 'q']:
            return 'quit'
        elif command.lower() == 'voice':
            return 'voice'
        return command
    except (EOFError, KeyboardInterrupt):
        return 'quit'

# Main function
def run_jarvis():
    """Main function to run the Jarvis assistant with simple interaction."""
    print("Starting Jarvis...")
    speak("Hello! I am Jarvis, your personal assistant.")
    
    try:
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Start the emotion detector
        if emotion_detector:
            try:
                emotion_detector.start()
                print("Emotion detection started.")
            except Exception as e:
                print(f"Warning: Could not start emotion detector: {e}")
        
        # Start the activity monitor
        if activity_monitor:
            try:
                activity_monitor.start()
                print("Activity monitoring started.")
            except Exception as e:
                print(f"Warning: Could not start activity monitor: {e}")
        
        # Start the reminder system
        if reminder_system:
            try:
                reminder_system.start()
                print("Reminder system started.")
            except Exception as e:
                print(f"Warning: Could not start reminder system: {e}")
        
        # Initial greeting
        print("Jarvis is now active. Say 'Hey Jarvis' to wake me up!")
        print("Press Ctrl+C to exit.")
        speak("Hello! I am Jarvis, your personal assistant. I'm now online and ready to assist you.")
        
        # Main interaction loop
        while not shutdown_flag:
            try:
                # Wait for user to say "Jarvis"
                print("\nListening for wake word... (say 'Jarvis')")
                wake_word_detected = listen_for_wake_word()
                
                if wake_word_detected and not shutdown_flag:
                    speak("Yes sir")
                    
                    # Get user command
                    print("Listening for command...")
                    command = get_input("What can I do for you, sir?")
                    
                    if command and command.strip() and not shutdown_flag:
                        speak("Okay sir")
                        print(f"Executing: {command}")
                        
                        # Process the command
                        response = process_command(command)
                        
                        # Speak the result
                        if response and response.strip():
                            speak(f"{response} sir")
                        else:
                            speak("Task completed sir")
                    
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                print("\nShutting down Jarvis...")
                shutdown_flag = True
                break
                
            except Exception as e:
                print(f"Error: {e}")
                speak("I encountered an error, sir")
                time.sleep(1)
    
    finally:
        # Clean up resources
        print("Shutting down components...")
        
        # Stop the emotion detector
        if hasattr(emotion_detector, 'stop'):
            emotion_detector.stop()
            print("Emotion detection stopped.")
        
        # Stop the activity monitor
        if hasattr(activity_monitor, 'stop'):
            activity_monitor.stop()
            print("Activity monitoring stopped.")
        
        # Stop the reminder system
        if hasattr(reminder_system, 'stop'):
            reminder_system.stop()
            print("Reminder system stopped.")
        
        # Save any pending data
        if hasattr(memory, '_save_memory'):
            memory._save_memory()
            print("Memory saved.")
        
        print("Goodbye!")

if __name__ == "__main__":
    run_jarvis()