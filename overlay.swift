import Cocoa
import WebKit

class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSPanel!
    var webView: WKWebView!
    
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
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Clean up window resources
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
