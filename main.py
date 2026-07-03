import time
import sys
from jarvis_listener import JarvisListener
from jarvis_agent import process_command, speak_feedback

def main():
    print("="*50)
    print("           J A R V I S   V O I C E   O S           ")
    print("         100% Offline & Visual Assistant           ")
    print("="*50)
    
    speak_feedback("Jarvis is online.")
    
    # Start the offline listener, pointing to the compiled swift binary
    listener = JarvisListener(binary_path="./listener", silence_timeout=1.5)
    
    # Whenever the listener finishes transcribing a spoken phrase,
    # it sends it to process_command which queries Ollama and automates the OS.
    success = listener.start(process_command)
    
    if not success:
        print("[Jarvis] Initialization failed.")
        return
        
    print("\n[Jarvis] Listening active. Say 'Jarvis, open Safari' or 'Jarvis, search for Python on Chrome'...")
    print("Press Ctrl+C to terminate.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Jarvis...")
        listener.stop()
        speak_feedback("Jarvis is offline.")

if __name__ == "__main__":
    main()
