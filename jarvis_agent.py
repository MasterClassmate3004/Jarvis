import json
import urllib.request
import urllib.error
import sys
import time
import subprocess
import threading
from jarvis_automation import focus_app, visual_type, press_key, trigger_shortcut, search_browser

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2" # Users can download Llama 3.2 3B or Qwen 2.5 3B

SYSTEM_PROMPT = """
You are Jarvis, a voice-controlled desktop assistant for macOS.
Your goal is to parse the user's spoken command and translate it into a structured JSON action that our native automation engine can execute.
The user wants to see actions happen visually (like opening apps and typing text).

You MUST respond ONLY with a single JSON object. Do not include any explanation, markdown, or other text outside the JSON.

Choose one of the following JSON schemas to respond with:

1. To open/focus an application:
{
  "action": "focus_app",
  "app": "Application Name" (e.g., "Safari", "Google Chrome", "Slack", "Notes", "Spotify", "FaceTime", "Calendar")
}

2. To search the web using a browser (Safari or Google Chrome):
{
  "action": "search",
  "browser": "Safari" or "Google Chrome",
  "query": "search query here"
}

3. To open an app and visually type text/prompt into it:
{
  "action": "type_in_app",
  "app": "Application Name",
  "text": "text to type here"
}

4. To press a special key (like enter/return, tab, space, escape, backspace):
{
  "action": "system_key",
  "key": "return" or "tab" or "space" or "escape" or "delete"
}

5. To trigger a keyboard shortcut:
{
  "action": "shortcut",
  "modifiers": ["cmd", "ctrl", "alt", "shift"],
  "key": "key character"
}

6. If the command is a conversational query or you don't know what action to automate:
{
  "action": "unhandled",
  "message": "Your helpful response here"
}

EXAMPLES:
- User says: "open slack" -> {"action": "focus_app", "app": "Slack"}
- User says: "search for cat videos on chrome" -> {"action": "search", "browser": "Google Chrome", "query": "cat videos"}
- User says: "type hello world in notes" -> {"action": "type_in_app", "app": "Notes", "text": "hello world"}
- User says: "press enter" -> {"action": "system_key", "key": "return"}
- User says: "copy that" -> {"action": "shortcut", "modifiers": ["cmd"], "key": "c"}
- User says: "who created you?" -> {"action": "unhandled", "message": "I am Jarvis, your visual macOS voice assistant."}
"""

_active_say_process = None
_say_lock = threading.Lock()

def speak_feedback(text):
    """Speaks feedback text to the user in a separate thread, interrupting any active speech."""
    global _active_say_process
    
    if _active_say_process:
        try:
            _active_say_process.terminate()
        except Exception:
            pass
            
    def run_say():
        global _active_say_process
        with _say_lock:
            import jarvis_server
            jarvis_server.set_state("SPEAKING", text)
            try:
                _active_say_process = subprocess.Popen(["say", text])
                _active_say_process.wait()
            except Exception:
                pass
            finally:
                _active_say_process = None
                
            # Only revert to READY if the state wasn't changed to TYPING/THINKING in the meantime
            if jarvis_server._current_state == "SPEAKING":
                jarvis_server.set_state("READY")
    threading.Thread(target=run_say, daemon=True).start()

def query_ollama(command, model=DEFAULT_MODEL):
    """Sends the command to the local Ollama server and retrieves the JSON response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": command}
        ],
        "stream": False,
        "options": {
            "temperature": 0.0
        },
        "format": "json"
    }
    
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            content_str = res_json.get("message", {}).get("content", "").strip()
            return json.loads(content_str)
    except urllib.error.URLError as e:
        print(f"\n[Jarvis Agent Error] Cannot connect to local Ollama. Is Ollama running? Error: {e}", file=sys.stderr)
        return {
            "action": "unhandled", 
            "message": "I cannot connect to Ollama. Please ensure the Ollama app is running locally."
        }
    except json.JSONDecodeError:
        print(f"\n[Jarvis Agent Error] Failed to parse JSON response from Ollama.", file=sys.stderr)
        return {"action": "unhandled", "message": "I encountered an error parsing that command."}
    except Exception as e:
        print(f"\n[Jarvis Agent Error] Unexpected error: {e}", file=sys.stderr)
        return {"action": "unhandled", "message": "An unexpected error occurred."}

def execute_action(action_json):
    """Executes the mapped native system action based on the parsed JSON from Ollama."""
    import jarvis_server
    action = action_json.get("action")
    if not action:
        print("[Jarvis Agent] Invalid action format.")
        return False
        
    print(f"[Jarvis Agent] Action: {action}")
    success = False
    
    if action == "focus_app":
        app = action_json.get("app")
        print(f"-> Focusing {app}")
        speak_feedback(f"Opening {app}")
        success = focus_app(app)
        
    elif action == "search":
        browser = action_json.get("browser", "Safari")
        query = action_json.get("query")
        print(f"-> Searching browser '{browser}' for: '{query}'")
        speak_feedback(f"Searching for {query}")
        jarvis_server.set_state("TYPING", f"Searching for '{query}'...")
        success = search_browser(browser, query)
        
    elif action == "type_in_app":
        app = action_json.get("app")
        text = action_json.get("text")
        print(f"-> Focusing {app} and typing: '{text}'")
        speak_feedback(f"Typing in {app}")
        jarvis_server.set_state("TYPING", text)
        if focus_app(app):
            time.sleep(0.5)
            success = visual_type(text, delay=0.015)
        
    elif action == "system_key":
        key = action_json.get("key")
        print(f"-> Pressing key: '{key}'")
        success = press_key(key)
        
    elif action == "shortcut":
        modifiers = action_json.get("modifiers", [])
        key = action_json.get("key")
        print(f"-> Shortcut: {modifiers} + {key}")
        success = trigger_shortcut(modifiers, key)
        
    elif action == "unhandled":
        msg = action_json.get("message", "I am not sure how to perform that action.")
        print(f"-> Jarvis Feedback: {msg}")
        speak_feedback(msg)
        success = True
    
    else:
        print(f"-> Unknown action: {action}")
        success = False
        
    # Revert state to READY at the end, EXCEPT if the action was focus_app or unhandled
    # (since those actions ONLY call speak_feedback, and the background say thread will handle the READY transition).
    if action not in ["focus_app", "unhandled"]:
        jarvis_server.set_state("READY")
        
    return success

def process_command(command, model=DEFAULT_MODEL):
    """Integrates LLM querying and action execution."""
    import jarvis_server
    print(f"\n[Jarvis Agent] User said: '{command}'")
    jarvis_server.set_state("THINKING", command)
    action_json = query_ollama(command, model=model)
    print(f"[Jarvis Agent] LLM Plan: {json.dumps(action_json, indent=2)}")
    execute_action(action_json)

if __name__ == "__main__":
    # Test query
    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        process_command(cmd)
    else:
        print("Usage: python3 jarvis_agent.py '<spoken command>'")
        print("Example: python3 jarvis_agent.py 'open Safari'")
