import time
import sys
import os
import subprocess
from jarvis_listener import JarvisListener
from jarvis_agent import process_command, speak_feedback
import jarvis_server

def compile_overlay():
    if os.path.exists("overlay.swift"):
        print("[Jarvis] Compiling visual overlay App Bundle...")
        try:
            # Ensure target directories exist inside the bundle
            os.makedirs("overlay.app/Contents/MacOS", exist_ok=True)
            
            # Copy Info-overlay.plist to the bundle structure
            if os.path.exists("Info-overlay.plist"):
                subprocess.run(["cp", "Info-overlay.plist", "overlay.app/Contents/Info.plist"], check=True)
            
            sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"]).decode('utf-8').strip()
            
            # Compile Swift code directly into the bundle
            subprocess.run([
                "swiftc",
                "-sdk", sdk_path,
                "-framework", "Cocoa",
                "-framework", "WebKit",
                "-framework", "Speech",
                "-framework", "AVFoundation",
                "overlay.swift",
                "-o", "overlay.app/Contents/MacOS/overlay"
            ], check=True)
            
            # Sign the entire bundle structure so macOS accepts the Info.plist usage descriptions
            subprocess.run(["codesign", "--force", "--deep", "--sign", "-", "overlay.app"], check=True)
            print("[Jarvis] Visual overlay compiled and signed successfully.")
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
    if compile_overlay():
        if os.path.exists("overlay.app"):
            print("[Jarvis] Starting visual overlay UI...")
            subprocess.Popen(["open", "overlay.app"])
    
    speak_feedback("Jarvis is online.")
    
    # Start the offline listener manager
    listener = JarvisListener(silence_timeout=1.5)
    
    # Whenever the listener finishes transcribing a spoken phrase,
    # it sends it to process_command which queries Ollama and automates the OS.
    success = listener.start(process_command)
    
    if not success:
        print("[Jarvis] Initialization failed.")
        subprocess.run(["killall", "overlay"], stderr=subprocess.DEVNULL)
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
        print("[Jarvis] Stopping visual overlay UI...")
        subprocess.run(["killall", "overlay"], stderr=subprocess.DEVNULL)
                
        # Stop HTTP server
        jarvis_server.stop_server()
        
        speak_feedback("Jarvis is offline.")

if __name__ == "__main__":
    main()
