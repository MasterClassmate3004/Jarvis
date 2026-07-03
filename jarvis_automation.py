import subprocess
import time
import sys

def run_applescript(script_content):
    """Executes a block of AppleScript and returns the output/errors."""
    process = subprocess.Popen(
        ['osascript', '-'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(script_content)
    if process.returncode != 0:
        print(f"AppleScript Error: {stderr.strip()}", file=sys.stderr)
        return False, stderr.strip()
    return True, stdout.strip()

def focus_app(app_name):
    """Brings the specified application to the foreground."""
    script = f'''
    tell application "{app_name}"
        activate
    end tell
    '''
    success, err = run_applescript(script)
    if not success and "does not understand" in err:
        # Fallback if application name has a slight variation
        script_fallback = f'''
        tell application "System Events"
            tell (first application process whose name contains "{app_name}")
                set frontmost to true
            end tell
        end tell
        '''
        success, _ = run_applescript(script_fallback)
    return success

def visual_type(text, delay=0.015):
    """Types the given text character-by-character with a visual delay."""
    # To type special characters safely, we can split the string and send keystrokes.
    # We escape double quotes and backslashes in AppleScript.
    escaped_text = text.replace('\\', '\\\\').replace('"', '\\"')
    
    script = f'''
    tell application "System Events"
        set txt to "{escaped_text}"
        repeat with char in characters of txt
            keystroke char
            delay {delay}
        end repeat
    end tell
    '''
    success, _ = run_applescript(script)
    return success

def press_key(key_name):
    """Presses a special key (e.g., return, tab, space, escape, backspace)."""
    special_keys = {
        "return": "return",
        "enter": "return",
        "tab": "tab",
        "space": "space",
        "escape": "escape",
        "esc": "escape",
        "delete": "delete",
        "backspace": "delete"
    }
    
    key = special_keys.get(key_name.lower())
    if not key:
        print(f"Unknown special key: {key_name}", file=sys.stderr)
        return False
        
    script = f'''
    tell application "System Events"
        key code {get_key_code(key)}
    end tell
    '''
    success, _ = run_applescript(script)
    return success

def get_key_code(key_name):
    """Returns the macOS keycode for common keys."""
    key_codes = {
        "return": 36,
        "tab": 48,
        "space": 49,
        "escape": 53,
        "delete": 51
    }
    return key_codes.get(key_name, 36)

def trigger_shortcut(modifiers, key):
    """Triggers a keyboard shortcut (e.g., cmd+l, cmd+t, cmd+w).
    
    modifiers: list of strings (e.g. ['command'], ['command', 'option'])
    key: char or string (e.g. 'l', 't', 'space')
    """
    mod_mapping = {
        "cmd": "command down",
        "command": "command down",
        "ctrl": "control down",
        "control": "control down",
        "alt": "option down",
        "option": "option down",
        "shift": "shift down"
    }
    
    mods = [mod_mapping[m.lower()] for m in modifiers if m.lower() in mod_mapping]
    mods_str = ", ".join(mods)
    
    # Check if key is a character or special key
    if len(key) == 1:
        script = f'''
        tell application "System Events"
            keystroke "{key}" using {{{mods_str}}}
        end tell
        '''
    else:
        # Special key code shortcut
        script = f'''
        tell application "System Events"
            key code {get_key_code(key)} using {{{mods_str}}}
        end tell
        '''
        
    success, _ = run_applescript(script)
    return success

def search_browser(browser_name, query):
    """Helper method to open a browser, focus the address bar, and search."""
    if not focus_app(browser_name):
        print(f"Failed to focus {browser_name}")
        return False
        
    time.sleep(0.5) # Wait for focus transit
    # Focus address bar (Cmd + L)
    trigger_shortcut(["command"], "l")
    time.sleep(0.2)
    
    # Type search query (visual speed) and press enter
    search_url = f"https://www.google.com/search?q={query}"
    visual_type(search_url, delay=0.01)
    time.sleep(0.2)
    press_key("return")
    return True

if __name__ == "__main__":
    # Quick test to verify functioning
    print("Testing Jarvis Automation Layer...")
    print("1. Focusing Safari...")
    # Try focusing Safari
    focused = focus_app("Safari")
    if focused:
        print("Focused Safari. Let's open a new tab (Cmd + T)...")
        time.sleep(0.5)
        trigger_shortcut(["command"], "t")
        time.sleep(0.5)
        print("Visual typing search query...")
        visual_type("https://www.google.com", delay=0.015)
        press_key("return")
    else:
        print("Safari could not be focused.")
