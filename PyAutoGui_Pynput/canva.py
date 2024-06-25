import sys
import ast
import time
from threading import Thread
from PyQt5.QtCore import QUrl, pyqtSlot, QObject, Qt, QTimer
from PyQt5.QtWidgets import QMainWindow, QApplication, QToolBar, QFrame, QSplitter, QVBoxLayout, QTextEdit, QTabWidget, QToolButton, QLineEdit, QAction, QStatusBar
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from pynput import keyboard, mouse
import pyautogui

# Declare global variables
recording = False
stop_flag = False
scroll_position = 0
record_val = False

# Mapping for special keys
key_mapping = {
    'Key.space': 'space', 'Key.enter': 'enter', 'Key.tab': 'tab', 'Key.backspace': 'backspace',
    'Key.esc': 'esc', 'Key.shift': 'shift', 'Key.shift_r': 'shift', 'Key.ctrl_l': 'ctrl',
    'Key.ctrl_r': 'ctrl', 'Key.alt_l': 'alt', 'Key.alt_r': 'alt', 'Key.caps_lock': 'capslock',
    'Key.cmd': 'command', 'Key.cmd_r': 'command', 'Key.delete': 'delete', 'Key.home': 'home',
    'Key.end': 'end', 'Key.page_up': 'pageup', 'Key.page_down': 'pagedown', 'Key.up': 'up',
    'Key.down': 'down', 'Key.left': 'left', 'Key.right': 'right', 'Key.f1': 'f1', 'Key.f2': 'f2',
    'Key.f3': 'f3', 'Key.f4': 'f4', 'Key.f5': 'f5', 'Key.f6': 'f6', 'Key.f7': 'f7', 'Key.f8': 'f8',
    'Key.f9': 'f9', 'Key.f10': 'f10', 'Key.f11': 'f11', 'Key.f12': 'f12'
}

class CustomWebEngineView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super(CustomWebEngineView, self).__init__(*args, **kwargs)
        self.recording = False

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # print(f"JavaScript console message: {message} (line {lineNumber}, source {sourceID})")
        return ""

class WebChannelHandler(QObject):
    @pyqtSlot(int)
    def scrollEvent(self, delta):
        global scroll_position
        scroll_position += delta
        direction = 'scrolldown' if delta > 0 else 'scrollup'
        print(f"Scroll event received in PyQt5: {direction}, {abs(delta)}, 0")
        if recording:
            with open('keylogging.txt', 'a') as file:
                file.write(f"['{direction}', {abs(delta)*6}, 0],\n")
            print(f"Scroll event recorded: {direction}, {abs(delta)*6}, 0")

class WebEnginePage(QWebEnginePage):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        self.main_window.handle_console_message(level, message, lineNumber, sourceId)

class NetworkRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def interceptRequest(self, info):
        request_url = info.requestUrl().toString()
        # print("Intercepting request:", request_url)
        self.main_window.handle_network_request(request_url)

class MainWindow(QMainWindow):
    def __init__(self, url, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.initial_url = url

        # Set up the browser
        self.browser = CustomWebEngineView()
        self.page = WebEnginePage(self)
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(self.initial_url))
        self.browser.urlChanged.connect(self.update_urlbar)
        self.setCentralWidget(self.browser)

        # Creating the frame and tab widget
        self.frame = QFrame(self)
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.tab_widget = QTabWidget()
        
        # Creating the console and network tabs
        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)

        self.network_output = QTextEdit(self)
        self.network_output.setReadOnly(True)

        self.tab_widget.addTab(self.console_output, "Console")
        self.tab_widget.addTab(self.network_output, "Network")

        # Layout for the frame
        frame_layout = QVBoxLayout()
        frame_layout.addWidget(self.tab_widget)
        self.frame.setLayout(frame_layout)

        # Splitter to contain both browser and frame
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.browser)
        self.splitter.addWidget(self.frame)
        self.splitter.setSizes([800, 200])  # Initial sizes

        self.setCentralWidget(self.splitter)
        
        # Set up status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Navigation toolbar
        navtb = QToolBar("Navigation")
        self.addToolBar(navtb)

        # Record button
        self.record_btn = QToolButton(self)
        self.record_btn.setText("Start")
        self.record_btn.setStyleSheet("background-color: green")
        self.record_btn.setStatusTip("Toggle recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        navtb.addWidget(self.record_btn)

        # Play button
        play_btn = QAction("Play", self)
        play_btn.setStatusTip("Play the recorded script")
        play_btn.triggered.connect(self.play)
        navtb.addAction(play_btn)

        # Separator
        navtb.addSeparator()

        # URL bar
        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.urlbar)

        # Remove record in txt file
        rem_rec_btn = QAction("Remove Record", self)
        rem_rec_btn.setStatusTip("Remove the record script")
        rem_rec_btn.triggered.connect(self.remove_record)
        navtb.addAction(rem_rec_btn)

        # Stop button
        stop_btn = QAction("Stop", self)
        stop_btn.setStatusTip("Stop loading current page")
        stop_btn.triggered.connect(self.browser.stop)
        navtb.addAction(stop_btn)

        self.show()

        # Set up QWebChannel for communication
        self.channel = QWebChannel()
        self.browser.page().setWebChannel(self.channel)

        # Register the 'qt' object
        self.handler = WebChannelHandler()
        self.channel.registerObject('qt', self.handler)

        # Initialize logging attributes
        self.keylogger_listener = None
        self.mouse_listener = None

        # Set up network request interceptor
        self.interceptor = NetworkRequestInterceptor(self)
        self.browser.page().profile().setRequestInterceptor(self.interceptor)

        # Setup web channel after loading the page
        self.browser.page().loadFinished.connect(self.setup_web_channel)

        # Start the key listener thread
        self.key_listener_thread = Thread(target=self.listen_for_q_key)
        self.key_listener_thread.start()

    def setup_frames_and_tabs(self):
        self.frame = QFrame(self)
        self.tab_widget = QTabWidget()
        self.console_output = QTextEdit(self)
        self.console_output.setReadOnly(True)
        self.network_output = QTextEdit(self)
        self.network_output.setReadOnly(True)
        self.tab_widget.addTab(self.console_output, "Console")
        self.tab_widget.addTab(self.network_output, "Network")
        frame_layout = QVBoxLayout()
        frame_layout.addWidget(self.tab_widget)
        self.frame.setLayout(frame_layout)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.browser)
        self.splitter.addWidget(self.frame)
        self.splitter.setSizes([800, 200])
        self.setCentralWidget(self.splitter)

    def reset_scroll_position(self, url):
        current_url = url.toString()
        if current_url not in scroll_position:
            scroll_position[current_url] = 0

    def setup_web_channel(self):
        js = """
        (function() {
            var script = document.createElement('script');
            script.src = 'qrc:///qtwebchannel/qwebchannel.js';
            script.type = 'text/javascript';
            script.onload = function() {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.qt = channel.objects.qt;
                });
            };
            document.head.appendChild(script);
        })();
        """
        self.browser.page().runJavaScript(js)
        print("Web channel setup JavaScript injected.")

    def handle_console_message(self, level, message, line_number, source_id):
        console_message = f"Console message: {message} (Source: {source_id}, Line: {line_number})"
        if "warning" in message.lower():
            self.console_output.append(f'<hr><spanstyle="color: yellow;">{console_message}</spanstyle=>')
        elif "error" in message.lower():
            self.console_output.append(f'<hr><span style="color: red;">{console_message}</span>')
        else:
            self.console_output.append(f'<hr><span style="color: black;">{console_message}</span>')

    def handle_network_request(self, request_url):
        self.network_output.append(f'<hr><span style="color: black;">Network request: {request_url}</span>')
        # print(f"Network request: {request_url}")

    def inject_javascript(self):
        js_code = """
        (function() {
            if (window.scrollEventListener) {
                window.removeEventListener('scroll', window.scrollEventListener);
            }
            window.scrollEventListener = function(event) {
                var delta = event.deltaY || event.detail || event.wheelDelta;
                if (window.qt) {
                    window.qt.scrollEvent(delta);
                }
            };
            window.addEventListener('wheel', window.scrollEventListener);
            console.log('Scroll event listener set up');
        })();
        """
        self.browser.page().runJavaScript(js_code)
        print("JavaScript for scroll event listener injected.")

    def remove_javascript(self):
        js_code = """
        (function() {
            if (window.scrollEventListener) {
                window.removeEventListener('wheel', window.scrollEventListener);
                window.scrollEventListener = null;
                console.log('Scroll event listener removed');
            }
        })();
        """
        self.browser.page().runJavaScript(js_code)
        print("JavaScript for scroll event listener removal injected.")

    def run_autogui_in_thread(self):
        autogui_thread = Thread(target=self.autogui)
        autogui_thread.start()

    def autogui(self):
        with open('keylogging.txt', 'r') as f:
            file = f.read()

        file2 = ast.literal_eval('[' + file + ']')

        global record_val
        scroll_val = False
        for i in file2:
            if not record_val:
                if len(i) == 1:
                    key = i[0]
                    if key in key_mapping:
                        pyautogui.press(key_mapping[key])
                    else:
                        pyautogui.write(key)
                
                if "scrolldown" in i:
                    if scroll_val is True:
                        print("time sleep 2 sec for navigation")
                        time.sleep(2)
                        pyautogui.scroll(-i[1])
                        scroll_val = False
                    else:
                        pyautogui.scroll(-i[1])
                
                if "scrollup" in i:
                    if scroll_val is True:
                        print("time sleep 2 sec for navigation")
                        time.sleep(2)
                        pyautogui.scroll(i[1])
                        scroll_val = False
                    else:
                        pyautogui.scroll(i[1])

                if len(i) == 2:
                    pyautogui.moveTo(i[0], i[1])

                if len(i) == 4:
                    if i[3] == 'pressed' and scroll_val is False:
                        pyautogui.mouseDown(i[0], i[1], button=i[2][7:])
                        scroll_val = True

                    elif i[3] == 'pressed':
                        pyautogui.mouseDown(i[0], i[1], button=i[2][7:])

                    elif i[3] == 'released':
                        pyautogui.mouseUp(i[0], i[1], button=i[2][7:])
                        print("time sleep for 2 second")
                        time.sleep(2)
            else:
                print("Script break", "+++++++++++++++++++++++++++++++++++++++++++++++++")
                break

    def toggle_recording(self):
        global recording, stop_flag, scroll_position
        recording = not recording
        stop_flag = not recording  # Set stop_flag to True when recording stops
        scroll_position = 0  # Reset scroll position when recording starts
        self.browser.recording = recording
        if recording:
            self.record_btn.setStyleSheet("background-color: red")
            self.record_btn.setText("Pause")
            self.start_logging()
            self.inject_javascript()
            self.setup_web_channel()
        else:
            self.record_btn.setStyleSheet("background-color: green")
            self.record_btn.setText("Start")
            self.stop_logging()
            self.remove_javascript()
        print(f"Recording state: {recording}")

    def play(self):
        global record_val
        record_val = False
        self.browser.setUrl(QUrl(self.initial_url))
        time.sleep(1)
        self.run_autogui_in_thread()

    def remove_record(self):
        open("keylogging.txt","w").close()

    def update_urlbar(self, q):
        self.setup_web_channel()
        self.inject_javascript()
        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)

    def navigate_to_url(self):
        q = QUrl(self.urlbar.text())
        if q.scheme() == "":
            q.setScheme("http")
        self.browser.setUrl(q)

    def start_logging(self):
        self.keylogger_thread = Thread(target=self.keylogger)
        self.keylogger_thread.start()

        self.mouse_thread = Thread(target=self.mouse_logger)
        self.mouse_thread.start()

    def stop_logging(self):
        global stop_flag
        stop_flag = True
        if self.keylogger_listener is not None:
            self.keylogger_listener.stop()
        if self.mouse_listener is not None:
            self.mouse_listener.stop()

    def keylogger(self):
        def on_press(key):
            global stop_flag
            if stop_flag:
                return False  # Stop listener
            try:
                with open('keylogging.txt', 'a') as f:
                    f.write(f"['{key.char}'],\n")
            except AttributeError:
                with open('keylogging.txt', 'a') as f:
                    f.write(f"['{key}'],\n")

        def on_release(key):
            global stop_flag
            if key == keyboard.Key.esc:
                self.remove_javascript()
                stop_flag = True
                return False

        self.keylogger_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keylogger_listener.start()
        self.keylogger_listener.join()

    def mouse_logger(self):
        def on_move(x, y):
            global stop_flag
            if stop_flag:
                return False  # Stop listener
            with open('keylogging.txt', 'a') as f:
                f.write(f'[{x}, {y}],\n')

        def on_click(x, y, button, pressed):
            global stop_flag
            if stop_flag:
                return False  # Stop listener
            
            with open('keylogging.txt', 'a') as f:
                if pressed:
                    f.write(f"[{x}, {y}, '{button}', 'pressed'],\n")
                else:
                    f.write(f"[{x}, {y}, '{button}', 'released'],\n")

        self.mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
        self.mouse_listener.start()
        self.mouse_listener.wait()

    def record_val_loop(self):
        return True

    def listen_for_q_key(self):
        def on_press(key):
            if key == keyboard.KeyCode.from_char('s'):
                global record_val
                print("Q key pressed. Closing application.")
                record_val = self.record_val_loop()
                print(record_val,"++++++++++++++++++++")

            if key == keyboard.KeyCode.from_char("q"):
                self.close()
                
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

# Creating a PyQt5 application
app = QApplication(sys.argv)
app.setApplicationName("Geek Browser")

# Creating a main window object
url = "https://en.wikipedia.org/wiki/Empire"
window = MainWindow(url)

# Start the application loop
app.exec_()