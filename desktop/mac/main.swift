// superHuy cho macOS: ứng dụng gốc (AppKit + WKWebView) mở app.roimaxxhub.com/app trong cửa sổ riêng.
// Đăng nhập bằng mã PIN của superHuy; phiên, cookie lưu riêng cho app. Không chứa bí mật nào.
import Cocoa
import WebKit

let APP_URL = URL(string: "https://app.roimaxxhub.com/app?src=mac")!
let HOST = "app.roimaxxhub.com"

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    var window: NSWindow!
    var web: WKWebView!

    func applicationDidFinishLaunching(_ n: Notification) {
        buildMenu()
        let cfg = WKWebViewConfiguration()
        cfg.websiteDataStore = .default()
        cfg.preferences.javaScriptCanOpenWindowsAutomatically = true
        cfg.mediaTypesRequiringUserActionForPlayback = []
        cfg.applicationNameForUserAgent = "superHuyMac/1.0 Version/17.0 Safari/605.1.15"
        web = WKWebView(frame: .zero, configuration: cfg)
        web.navigationDelegate = self
        web.uiDelegate = self
        web.allowsBackForwardNavigationGestures = true
        web.allowsMagnification = true
        if #available(macOS 13.3, *) { web.isInspectable = false }

        let frame = NSRect(x: 0, y: 0, width: 460, height: 900)
        window = NSWindow(contentRect: frame, styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.title = "superHuy"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.minSize = NSSize(width: 380, height: 560)
        window.backgroundColor = NSColor(red: 0.957, green: 0.945, blue: 0.973, alpha: 1)
        window.contentView = web
        window.setFrameAutosaveName("superHuyMain")
        if !window.setFrameUsingName("superHuyMain") { window.center() }
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        web.load(URLRequest(url: APP_URL))
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ s: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { window.makeKeyAndOrderFront(nil) }
        return true
    }

    // Liên kết ra ngoài superHuy (bài gốc, GitHub, YouTube...) mở bằng trình duyệt mặc định
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if a.shouldPerformDownload { decisionHandler(.download); return }
        if let u = a.request.url, let h = u.host, h != HOST, ["http", "https"].contains(u.scheme ?? ""), a.targetFrame?.isMainFrame ?? true {
            NSWorkspace.shared.open(u); decisionHandler(.cancel); return
        }
        decisionHandler(.allow)
    }
    func webView(_ w: WKWebView, decidePolicyFor r: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        if let h = r.response as? HTTPURLResponse, let cd = h.value(forHTTPHeaderField: "Content-Disposition"), cd.lowercased().contains("attachment") {
            decisionHandler(.download); return
        }
        decisionHandler(r.canShowMIMEType ? .allow : .download)
    }
    func webView(_ w: WKWebView, createWebViewWith c: WKWebViewConfiguration, for a: WKNavigationAction, windowFeatures f: WKWindowFeatures) -> WKWebView? {
        if let u = a.request.url { if u.host == HOST { w.load(URLRequest(url: u)) } else { NSWorkspace.shared.open(u) } }
        return nil
    }
    func webView(_ w: WKWebView, navigationAction a: WKNavigationAction, didBecome d: WKDownload) { d.delegate = self }
    func webView(_ w: WKWebView, navigationResponse r: WKNavigationResponse, didBecome d: WKDownload) { d.delegate = self }

    // Tải file (video reels, biên bản...) về thư mục Tải về
    func download(_ d: WKDownload, decideDestinationUsing r: URLResponse, suggestedFilename name: String, completionHandler: @escaping (URL?) -> Void) {
        let dir = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask)[0]
        var dest = dir.appendingPathComponent(name)
        var i = 2
        while FileManager.default.fileExists(atPath: dest.path) {
            dest = dir.appendingPathComponent("\((name as NSString).deletingPathExtension) (\(i)).\((name as NSString).pathExtension)"); i += 1
        }
        completionHandler(dest)
    }
    func downloadDidFinish(_ d: WKDownload) {
        NSWorkspace.shared.activateFileViewerSelecting([FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask)[0]])
    }

    // Chọn file để tải lên (ghi âm cuộc họp, ảnh...)
    func webView(_ w: WKWebView, runOpenPanelWith p: WKOpenPanelParameters, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let o = NSOpenPanel(); o.allowsMultipleSelection = p.allowsMultipleSelection; o.canChooseDirectories = false
        o.beginSheetModal(for: window) { r in completionHandler(r == .OK ? o.urls : nil) }
    }
    // Micro để ghi âm cuộc họp ngay trong app (chỉ cho trang superHuy)
    @available(macOS 12.0, *)
    func webView(_ w: WKWebView, requestMediaCapturePermissionFor o: WKSecurityOrigin, initiatedByFrame f: WKFrameInfo, type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(o.host == HOST ? .grant : .deny)
    }
    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping () -> Void) {
        let a = NSAlert(); a.messageText = m; a.beginSheetModal(for: window) { _ in completionHandler() }
    }
    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = m; a.addButton(withTitle: "OK"); a.addButton(withTitle: "Huỷ")
        a.beginSheetModal(for: window) { r in completionHandler(r == .alertFirstButtonReturn) }
    }
    func webView(_ w: WKWebView, didFail n: WKNavigation!, withError e: Error) { offline(e) }
    func webView(_ w: WKWebView, didFailProvisionalNavigation n: WKNavigation!, withError e: Error) { offline(e) }
    func offline(_ e: Error) {
        let html = """
        <html><body style="font:15px -apple-system;display:flex;height:100vh;align-items:center;justify-content:center;background:#F4F1F8;color:#15171A">
        <div style="text-align:center"><b style="font-size:18px">Chưa kết nối được superHuy</b><p style="color:#7C828A">Kiểm tra mạng rồi bấm ⌘R để tải lại.</p></div></body></html>
        """
        web.loadHTMLString(html, baseURL: nil)
    }

    @objc func reload() { web.load(URLRequest(url: APP_URL)) }
    @objc func goBack() { web.goBack() }
    @objc func zoomIn() { web.magnification = min(2, web.magnification + 0.1) }
    @objc func zoomOut() { web.magnification = max(0.6, web.magnification - 0.1) }
    @objc func zoomReset() { web.magnification = 1 }

    func buildMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem(); main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Giới thiệu superHuy", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Ẩn superHuy", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Thoát superHuy", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        let editItem = NSMenuItem(); main.addItem(editItem)
        let edit = NSMenu(title: "Sửa")
        edit.addItem(withTitle: "Hoàn tác", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Làm lại", action: Selector(("redo:")), keyEquivalent: "Z")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Cắt", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Sao chép", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Dán", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Chọn tất cả", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = edit
        let viewItem = NSMenuItem(); main.addItem(viewItem)
        let view = NSMenu(title: "Xem")
        view.addItem(withTitle: "Tải lại", action: #selector(reload), keyEquivalent: "r")
        view.addItem(withTitle: "Quay lại", action: #selector(goBack), keyEquivalent: "[")
        view.addItem(withTitle: "Phóng to", action: #selector(zoomIn), keyEquivalent: "+")
        view.addItem(withTitle: "Thu nhỏ", action: #selector(zoomOut), keyEquivalent: "-")
        view.addItem(withTitle: "Cỡ chuẩn", action: #selector(zoomReset), keyEquivalent: "0")
        viewItem.submenu = view
        let winItem = NSMenuItem(); main.addItem(winItem)
        let win = NSMenu(title: "Cửa sổ")
        win.addItem(withTitle: "Thu nhỏ", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        win.addItem(withTitle: "Đóng", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        winItem.submenu = win
        NSApp.mainMenu = main
        NSApp.windowsMenu = win
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
