import Foundation
import Speech
import AVFoundation

#if os(macOS)

class SpeechListener {
    private let speechRecognizer: SFSpeechRecognizer
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()
    
    init?() {
        guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US")) else {
            print("ERROR: Speech recognizer not available for en-US")
            fflush(stdout)
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
                fflush(stdout)
                exit(1)
            case .restricted:
                print("ERROR: Speech recognition restricted on this device")
                fflush(stdout)
                exit(1)
            case .notDetermined:
                print("ERROR: Speech recognition authorization not determined")
                fflush(stdout)
                exit(1)
            @unknown default:
                print("ERROR: Unknown authorization status")
                fflush(stdout)
                exit(1)
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
            fflush(stdout)
            exit(1)
        }
        
        // Force on-device (offline) speech recognition
        recognitionRequest.requiresOnDeviceRecognition = true
        recognitionRequest.shouldReportPartialResults = true
        
        let inputNode = audioEngine.inputNode
        
        // Use default input format (usually 44100Hz or 48000Hz)
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { (buffer, when) in
            self.recognitionRequest?.append(buffer)
        }
        
        recognitionTask = speechRecognizer.recognitionTask(with: recognitionRequest) { result, error in
            if let result = result {
                let transcription = result.bestTranscription.formattedString
                print("TRANSCRIPT:\(transcription)")
                fflush(stdout)
            }
            
            if let error = error {
                // Ignore transient errors that don't stop the recognition
                let nsError = error as NSError
                if nsError.domain == "kAUSetInputFormatError" || nsError.code == 203 {
                    // 203 is standard pause/retry code in Apple speech
                    return
                }
                print("ERROR:\(error.localizedDescription)")
                fflush(stdout)
                self.stop()
                exit(1)
            }
        }
        
        do {
            audioEngine.prepare()
            try audioEngine.start()
            print("READY: Listening...")
            fflush(stdout)
        } catch {
            print("ERROR: Audio engine failed to start: \(error.localizedDescription)")
            fflush(stdout)
            exit(1)
        }
    }
    
    func stop() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()
    }
}

guard let listener = SpeechListener() else {
    exit(1)
}

listener.start()

// Run loop to keep the CLI alive
RunLoop.main.run()

#endif
