import time
import sys
import os
import subprocess
from jarvis_listener import JarvisListener
from jarvis_agent import process_command, speak_feedback
import jarvis_server

def compile_overlay():
    if os.path.exists("overlay.swift"):
        print("[Jarvis] Compiling visual overlay...")
        try:
            sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"]).decode('utf-8').strip()
            subprocess.run([
                "swiftc",
                "-sdk", sdk_path,
                "-framework", "Cocoa",
                "-framework", "WebKit",
                "overlay.swift",
                "-o", "overlay"
            ], check=True)
            print("[Jarvis] Visual overlay compiled successfully.")
            return True
        except Exception as e:
            print(f"[Jarvis Error] Failed to compile overlay: {e}")
            return False
    else:
        print("[Jarvis Error] overlay.swift not found.")
        return False

def main():
    print("="*50)
    print("           J A R V I S   V O I C E   O S           ")
    print("         100% Offline & Visual Assistant           ")
    print("="*50)
    
    # 1. Start the HTTP SSE server in the background
    jarvis_server.start_server(port=8000)
    
    # 2. Compile and launch the overlay UI
    overlay_process = None
    if compile_overlay():
        if os.path.exists("./overlay"):
            print("[Jarvis] Starting visual overlay UI...")
            overlay_process = subprocess.Popen(["./overlay"])
    
    speak_feedback("Jarvis is online.")
    
    # Start the offline listener, pointing to the compiled swift binary
    listener = JarvisListener(binary_path="./listener", silence_timeout=1.5)
    
    # Whenever the listener finishes transcribing a spoken phrase,
    # it sends it to process_command which queries Ollama and automates the OS.
    success = listener.start(process_command)
    
    if not success:
        print("[Jarvis] Initialization failed.")
        if overlay_process:
            overlay_process.terminate()
        jarvis_server.stop_server()
        return
        
    print("\n[Jarvis] Listening active. Say 'Jarvis, open Safari' or 'Jarvis, search for Python on Chrome'...")
    print("Press Ctrl+C to terminate.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Jarvis...")
        listener.stop()
        
        # Stop overlay UI process
        if overlay_process:
            print("[Jarvis] Stopping visual overlay UI...")
            overlay_process.terminate()
            try:
                overlay_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                overlay_process.kill()
                
        # Stop HTTP server
        jarvis_server.stop_server()
        
        speak_feedback("Jarvis is offline.")

if __name__ == "__main__":
    main()
