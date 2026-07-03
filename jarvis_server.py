import os
import sys
import json
import time
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Global list of active SSE clients
_clients = []
_clients_lock = threading.Lock()
_current_state = "READY"
_current_message = ""
_server_instance = None
_server_thread = None

UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui')

class JarvisHTTPHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Maps HTTP URL path to local directory file path
        # Normalize and strip query parameters/anchors
        url_path = path.split('?')[0].split('#')[0]
        relative_path = url_path.lstrip('/')
        
        # Prevent directory traversal
        clean_path = os.path.basename(relative_path) if relative_path else ""
        if not clean_path:
            clean_path = 'index.html'
            
        return os.path.join(UI_DIR, clean_path)

    def do_GET(self):
        global _clients, _current_state, _current_message
        
        if self.path.split('?')[0] == '/stream':
            # Establish Server-Sent Events stream
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Send initial state immediately
            initial_payload = json.dumps({"state": _current_state, "message": _current_message})
            try:
                self.wfile.write(f"data: {initial_payload}\n\n".encode('utf-8'))
                self.wfile.flush()
            except Exception:
                return
            
            # Add to clients
            with _clients_lock:
                _clients.append(self)
            
            # Keep the connection open until client disconnects
            try:
                while True:
                    # Send a comment keep-alive ping every 5 seconds to prevent browser timeouts
                    time.sleep(5)
                    try:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    except (ConnectionResetError, BrokenPipeError):
                        break
            except Exception:
                pass
            finally:
                with _clients_lock:
                    if self in _clients:
                        _clients.remove(self)
        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        if self.path == '/transcript':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                transcript = data.get('transcript', '')
                
                from jarvis_listener import handle_transcript_received
                handle_transcript_received(transcript)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f'{{"error":"{e}"}}'.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    # Disable default log messages to stdout to prevent polluting console output
    def log_message(self, format, *args):
        pass

def set_state(state, message=""):
    """Updates global state and broadcasts to all SSE clients."""
    global _current_state, _current_message
    _current_state = state
    _current_message = message
    
    payload = json.dumps({"state": state, "message": message})
    data_bytes = f"data: {payload}\n\n".encode('utf-8')
    
    with _clients_lock:
        active_clients = list(_clients)
        
    for client in active_clients:
        try:
            client.wfile.write(data_bytes)
            client.wfile.flush()
        except Exception:
            # Client disconnected, will be removed by do_GET finally block
            pass

def start_server(port=8000):
    """Starts the ThreadingHTTPServer in a background daemon thread."""
    global _server_instance, _server_thread
    
    # Ensure UI directory exists
    os.makedirs(UI_DIR, exist_ok=True)
    
    def run():
        global _server_instance
        try:
            _server_instance = ThreadingHTTPServer(('127.0.0.1', port), JarvisHTTPHandler)
            print(f"[Jarvis Server] Running UI server at http://127.0.0.1:{port}", flush=True)
            _server_instance.serve_forever()
        except Exception as e:
            print(f"[Jarvis Server Error] Server failed to start: {e}", file=sys.stderr)
            
    _server_thread = threading.Thread(target=run, daemon=True)
    _server_thread.start()
    time.sleep(0.5) # Wait for server to bind

def stop_server():
    """Stops the running server."""
    global _server_instance
    if _server_instance:
        _server_instance.shutdown()
        _server_instance.server_close()
        print("[Jarvis Server] Server stopped.", flush=True)
