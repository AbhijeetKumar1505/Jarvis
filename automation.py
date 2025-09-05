import platform

# Mouse movement and click
def move_mouse(x, y):
    import pyautogui
    pyautogui.moveTo(x, y)

def click(x, y):
    import pyautogui
    pyautogui.click(x, y)

# Keyboard typing
def type_text(text):
    import pyautogui
    pyautogui.write(text)

def press_key(key):
    import keyboard
    keyboard.press_and_release(key)

# System control functions
import pyautogui
import screen_brightness_control as sbc

def system_control(command, speak):
    if "volume up" in command:
        pyautogui.press('volumeup')
        speak("Volume increased sir")
    elif "volume down" in command:
        pyautogui.press('volumedown')
        speak("Volume decreased sir")
    elif "mute" in command:
        pyautogui.press('volumemute')
        speak("Sound muted sir")
    elif "brightness" in command:
        if "increase" in command:
            current = sbc.get_brightness()[0]
            sbc.set_brightness(current + 10)
            speak(f"Brightness increased to {current + 10}% sir")
        elif "decrease" in command:
            current = sbc.get_brightness()[0]
            sbc.set_brightness(max(0, current - 10))
            speak(f"Brightness decreased to {max(0, current - 10)}% sir")

# Screenshot
import datetime

def take_screenshot(speak=None):
    import pyautogui
    screenshot = pyautogui.screenshot()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    screenshot.save(filename)
    if speak:
        speak(f"Screenshot saved as {filename} sir")
    return filename

# Find image on screen
def find_on_screen(image_path):
    import pyautogui
    return pyautogui.locateOnScreen(image_path)

# Window management (cross-platform)
def get_windows():
    import pygetwindow as gw
    return gw.getAllTitles()

def focus_window(title):
    import pygetwindow as gw
    win = gw.getWindowsWithTitle(title)[0]
    win.activate()

# Windows-specific window focus
def win_focus_window(title):
    import pywinauto
    app = pywinauto.Application().connect(title=title)
    app.top_window().set_focus()

# Accessibility query (Windows)
def accessibility_query(element_name):
    import uiautomation as auto
    element = auto.WindowControl(searchDepth=1, Name=element_name)
    return element.Exists 

import webbrowser

def open_app(app_name, speak=None, ask_user_install_callback=None):
    import keyboard
    import pyautogui
    import pygetwindow as gw
    import time
    
    # 1. Press the Start button (Windows key)
    keyboard.press_and_release('windows')
    time.sleep(0.5)
    # 2. Type the app name
    pyautogui.write(app_name)
    time.sleep(0.5)
    # 3. Press Enter to open it
    keyboard.press_and_release('enter')
    # 4. Wait for a few seconds
    time.sleep(4)
    # 5. Detect whether the app window appeared
    windows = gw.getAllTitles()
    found = any(app_name.lower() in w.lower() for w in windows if w.strip())
    if found:
        if speak:
            speak(f"{app_name} opened successfully.")
        return True
    else:
        if speak:
            speak(f"The app {app_name} doesn't seem to be installed. Would you like me to install it for you?")
        if ask_user_install_callback:
            user_response = ask_user_install_callback(app_name)
            if user_response and user_response.lower() in ["yes", "y", "sure", "ok"]:
                # Try to open Microsoft Store or search for download
                known_store = False
                # Add more known apps and their store URLs if needed
                store_urls = {
                    "spotify": "ms-windows-store://pdp/?productid=9ncbcszsjrsb",
                    "netflix": "ms-windows-store://pdp/?productid=9wzdncrfj3tj",
                }
                app_key = app_name.lower()
                if app_key in store_urls:
                    webbrowser.open(store_urls[app_key])
                    known_store = True
                if not known_store:
                    # Open browser and search for download
                    webbrowser.open(f"https://www.bing.com/search?q=download+{app_name}")
                if speak:
                    speak(f"I've opened a browser to help you download {app_name}.")
                return False
        return False 