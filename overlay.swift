import Cocoa
import WebKit
import Speech
import AVFoundation

class SpeechListener {
    private let speechRecognizer: SFSpeechRecognizer
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()
    
    init?() {
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US")) else {
            print("ERROR: Speech recognizer not available for en-US")
            return nil
        }
        self.speechRecognizer = recognizer
    }
    
    func start() {
        SFSpeechRecognizer.requestAuthorization { authStatus in
            switch authStatus {
            case .authorized:
                self.startRecording()
            case .denied:
                print("ERROR: Speech recognition authorization denied")
            case .restricted:
                print("ERROR: Speech recognition restricted on this device")
            case .notDetermined:
                print("ERROR: Speech recognition authorization not determined")
            @unknown default:
                print("ERROR: Unknown authorization status")
            }
        }
    }
    
    private func startRecording() {
        if recognitionTask != nil {
            recognitionTask?.cancel()
            recognitionTask = nil
        }
        
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let recognitionRequest = recognitionRequest else {
            print("ERROR: Unable to create recognition request")
            return
        }
        
        recognitionRequest.requiresOnDeviceRecognition = true
        recognitionRequest.shouldReportPartialResults = true
        
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { (buffer, when) in
            self.recognitionRequest?.append(buffer)
        }
        
        recognitionTask = speechRecognizer.recognitionTask(with: recognitionRequest) { result, error in
            if let result = result {
                let transcription = result.bestTranscription.formattedString
                self.sendTranscript(transcription)
            }
            
            if let error = error {
                let nsError = error as NSError
                if nsError.domain == "kAUSetInputFormatError" || nsError.code == 203 {
                    return
                }
                print("ERROR: \(error.localizedDescription)")
                self.stop()
            }
        }
        
        do {
            audioEngine.prepare()
            try audioEngine.start()
        } catch {
            print("ERROR: Audio engine failed to start: \(error.localizedDescription)")
        }
    }
    
    func stop() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
    }
    
    private func sendTranscript(_ text: String) {
        guard let url = URL(string: "http://127.0.0.1:8000/transcript") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = ["transcript": text]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        let task = URLSession.shared.dataTask(with: request) { _, _, _ in }
        task.resume()
    }
}

class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSPanel!
    var webView: WKWebView!
    var listener: SpeechListener?
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide Dock icon so it runs purely as an overlay accessory
        NSApp.setActivationPolicy(.accessory)
        
        // Determine screen coordinates to place it top-center
        let screenFrame = NSScreen.main?.frame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let windowWidth: CGFloat = 430
        let windowHeight: CGFloat = 100
        
        let xPos = (screenFrame.width - windowWidth) / 2
        let yPos = screenFrame.height - windowHeight - 40
        
        // NSPanel with nonactivatingPanel ensures it stays floating on top but doesn't take focus
        window = NSPanel(
            contentRect: NSRect(x: xPos, y: yPos, width: windowWidth, height: windowHeight),
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        
        window.level = .statusBar // Floats above all windows and full screen apps
        window.backgroundColor = NSColor.clear
        window.isOpaque = false
        window.hasShadow = false
        window.isMovableByWindowBackground = true
        window.isMovable = true
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        
        // WebView configurations
        let webConfiguration = WKWebViewConfiguration()
        
        webView = WKWebView(frame: window.contentView!.bounds, configuration: webConfiguration)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground") // Transparent background
        
        // Load the local server
        if let url = URL(string: "http://127.0.0.1:8000") {
            webView.load(URLRequest(url: url))
        }
        
        window.contentView?.addSubview(webView)
        window.makeKeyAndOrderFront(nil)
        window.orderFrontRegardless()
        
        // Start offline speech recognition
        if let speechListener = SpeechListener() {
            self.listener = speechListener
            speechListener.start()
        }
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        listener?.stop()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
