import subprocess
import time
import sys
import threading
import os

class JarvisListener:
    def __init__(self, binary_path="./listener", silence_timeout=1.5, wake_word="jarvis"):
        self.binary_path = binary_path
        self.silence_timeout = silence_timeout
        self.wake_word = wake_word.lower()
        self.process = None
        self.last_transcript_time = time.time()
        self.current_transcript = ""
        self.command_callback = None
        self.is_listening = False
        self.monitor_thread = None
        self.reader_thread = None

    def start(self, callback):
        """Starts the listener subprocess and registers a callback for commands."""
        if not os.path.exists(self.binary_path):
            print(f"Error: Native listener binary not found at {self.binary_path}. Please compile listener.swift first.", file=sys.stderr)
            return False
            
        self.command_callback = callback
        self.is_listening = True
        
        # Start the native Swift listener as a subprocess
        self.process = subprocess.Popen(
            [self.binary_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Thread to read output from the Swift process stdout
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        
        # Thread to monitor speech timeouts (silence detection)
        self.monitor_thread = threading.Thread(target=self._monitor_silence, daemon=True)
        self.monitor_thread.start()
        
        return True

    def _read_output(self):
        """Reads stdout from the listener process line by line."""
        for line in iter(self.process.stdout.readline, ''):
            if not self.is_listening:
                break
                
            line = line.strip()
            if line.startswith("READY:"):
                print("[Jarvis] Ready and listening offline...")
            elif line.startswith("ERROR:"):
                print(f"[Jarvis Listener Error] {line[6:]}", file=sys.stderr)
            elif line.startswith("TRANSCRIPT:"):
                transcript = line[11:].strip()
                # Update transcription and time
                self.current_transcript = transcript
                self.last_transcript_time = time.time()
                print(f"[Jarvis Heard] {transcript}", flush=True)
                
        # Handle process termination
        if self.process.poll() is not None:
            err = self.process.stderr.read()
            if err:
                print(f"[Jarvis Listener STDERR] {err.strip()}", file=sys.stderr)

    def _monitor_silence(self):
        """Monitors silence and triggers callback when the user stops speaking."""
        while self.is_listening:
            time.sleep(0.1)
            # If we have a transcript and silence exceeds the timeout
            if self.current_transcript and (time.time() - self.last_transcript_time > self.silence_timeout):
                full_text = self.current_transcript.strip()
                self.current_transcript = "" # Reset transcript for next phrase
                
                # Check for wake word trigger or process command directly
                lower_text = full_text.lower()
                if self.wake_word in lower_text:
                    # Strip wake word and call callback
                    cmd_start = lower_text.find(self.wake_word) + len(self.wake_word)
                    command = full_text[cmd_start:].strip(",. ")
                    if command:
                        print(f"[Jarvis Action] Processing: '{command}'")
                        if self.command_callback:
                            self.command_callback(command)
                else:
                    # If we don't require the wake word strictly, or just process everything
                    print(f"[Jarvis Action] Direct command processed: '{full_text}'")
                    if self.command_callback:
                        self.command_callback(full_text)

    def stop(self):
        """Stops the listener and kills the subprocess."""
        self.is_listening = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
        print("[Jarvis] Stopped listening.")

if __name__ == "__main__":
    def dummy_callback(command):
        print(f"Callback triggered with command: {command}")

    listener = JarvisListener(binary_path="./listener", silence_timeout=1.5)
    print("Starting listener. Say 'Jarvis, open Safari'...")
    listener.start(dummy_callback)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
