import time
import sys
import threading

_active_listener = None

def handle_transcript_received(transcript):
    """Global callback triggered by the HTTP server when the overlay sends a transcript."""
    global _active_listener
    if _active_listener and _active_listener.is_listening:
        _active_listener.on_transcript(transcript)

class JarvisListener:
    def __init__(self, binary_path=None, silence_timeout=1.5, wake_word="jarvis"):
        self.silence_timeout = silence_timeout
        self.wake_word = wake_word.lower()
        self.last_transcript_time = time.time()
        self.current_transcript = ""
        self.command_callback = None
        self.is_listening = False
        self.monitor_thread = None

    def start(self, callback):
        """Starts the offline listener by listening to callbacks from the overlay."""
        global _active_listener
        self.command_callback = callback
        self.is_listening = True
        _active_listener = self
        
        # Thread to monitor speech timeouts (silence detection)
        self.monitor_thread = threading.Thread(target=self._monitor_silence, daemon=True)
        self.monitor_thread.start()
        
        print("[Jarvis] Listener initialized. Waiting for transcriptions from overlay...", flush=True)
        return True

    def on_transcript(self, transcript):
        """Called when a transcript is received via the HTTP server."""
        from jarvis_server import set_state
        self.current_transcript = transcript
        self.last_transcript_time = time.time()
        print(f"[Jarvis Heard] {transcript}", flush=True)
        set_state("TRANSCRIPT", transcript)

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
        """Stops the listener."""
        self.is_listening = False
        print("[Jarvis] Stopped listening.", flush=True)
