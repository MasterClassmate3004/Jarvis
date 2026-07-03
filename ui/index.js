const statusTextEl = document.querySelector('.status-text');
const transcriptEl = document.getElementById('transcript');
const bodyEl = document.body;

function updateUI(state, message) {
    console.log("State updated:", state, "Message:", message);
    
    // Reset body classes
    bodyEl.className = '';
    
    switch (state) {
        case 'READY':
            bodyEl.classList.add('state-ready');
            statusTextEl.textContent = 'LISTENING';
            if (message) {
                transcriptEl.textContent = message;
                transcriptEl.style.opacity = '1.0';
            } else {
                transcriptEl.textContent = 'Say "Jarvis" followed by a command...';
                transcriptEl.style.opacity = '0.5';
            }
            break;
            
        case 'TRANSCRIPT':
            // Stay in ready class visually (cyan visualizer) but update transcript text in real time
            bodyEl.classList.add('state-ready');
            statusTextEl.textContent = 'HEARING...';
            transcriptEl.textContent = message || '';
            transcriptEl.style.opacity = '1.0';
            break;
            
        case 'THINKING':
            bodyEl.classList.add('state-thinking');
            statusTextEl.textContent = 'THINKING';
            if (message) {
                transcriptEl.textContent = message;
            }
            transcriptEl.style.opacity = '0.7';
            break;
            
        case 'TYPING':
            bodyEl.classList.add('state-typing');
            statusTextEl.textContent = 'TYPING';
            if (message) {
                // Limit the typed text display size to look clean
                const displayMsg = message.length > 35 ? message.substring(0, 32) + '...' : message;
                transcriptEl.textContent = `Typing: "${displayMsg}"`;
            }
            transcriptEl.style.opacity = '1.0';
            break;
            
        case 'SPEAKING':
            bodyEl.classList.add('state-speaking');
            statusTextEl.textContent = 'SPEAKING';
            if (message) {
                transcriptEl.textContent = message;
            }
            transcriptEl.style.opacity = '1.0';
            break;
            
        default:
            bodyEl.classList.add('state-ready');
            statusTextEl.textContent = state;
            if (message) {
                transcriptEl.textContent = message;
            }
            break;
    }
}

// Establish Server-Sent Events stream to the Python server
function connectSSE() {
    console.log("Connecting to status stream...");
    const eventSource = new EventSource('/stream');
    
    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            updateUI(data.state, data.message);
        } catch (e) {
            console.error("Error parsing event data:", e);
        }
    };
    
    eventSource.onerror = function(err) {
        console.error("SSE connection error. Retrying in 2 seconds...", err);
        eventSource.close();
        // Retry connection in 2 seconds
        setTimeout(connectSSE, 2000);
    };
}

// Start connection
connectSSE();
