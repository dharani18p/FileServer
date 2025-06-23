import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import pyperclip
import threading
import time
import re
import pystray
from PIL import Image
import sys

def resource_path(relative_path):
    """ Get absolute path to resource for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ClipboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Saveetha Helping Hand")
        self.root.iconbitmap(resource_path("logo.ico"))  # Ensure this file exists
        self.root.geometry("800x600")
        
        # System tray setup
        self.tray_icon = None
        self.create_tray_icon()
        
        # GitHub configuration
        self.github_user = "dharani18p"
        self.repo_name = "FileServer"
        self.api_url = f"https://api.github.com/repos/{self.github_user}/{self.repo_name}/contents/"
        self.qa_pairs = {}
        self.monitoring = False
        self.exit_command = "saveethaguru"
        
        # Create UI components
        self.create_widgets()
        self.fetch_file_list()
        
        # Window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def create_tray_icon(self):
        """Initialize system tray icon and menu"""
        try:
            image = Image.open(resource_path("logo.ico"))  # Ensure this file exists
            menu = (
                pystray.MenuItem('Show', self.show_app),
                pystray.MenuItem('Exit', self.exit_app)
            )
            self.tray_icon = pystray.Icon("name", image, "Saveetha Helping Hand", menu)
        except Exception as e:
            print(f"Error creating tray icon: {e}")

    def create_widgets(self):
        """Initialize all GUI components"""
        # File selection frame
        file_frame = ttk.Frame(self.root, padding=10)
        file_frame.pack(fill=tk.X)
        
        self.file_combo = ttk.Combobox(file_frame, width=50, state="readonly")
        self.file_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(file_frame, text="Refresh", 
                 command=self.fetch_file_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="Load File", 
                 command=self.load_selected_file).pack(side=tk.LEFT, padx=5)
        
        # Hide button
        ttk.Button(file_frame, text="Hide to Tray", 
                 command=self.hide_to_tray).pack(side=tk.RIGHT, padx=5)

        # Control buttons
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(control_frame, text="Start Monitoring",
                                  state="disabled", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Monitoring",
                                 state="disabled", command=self.stop_monitoring)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(self.root, text="Status: Inactive",
                                    foreground="gray")
        self.status_label.pack(pady=5)

        # Log viewer
        log_frame = ttk.Frame(self.root)
        log_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def fetch_file_list(self):
        """Fetch list of TXT files from GitHub repository"""
        try:
            response = requests.get(self.api_url)
            response.raise_for_status()
            files = [f['name'] for f in response.json() 
                    if f['name'].lower().endswith('.txt')]
            self.file_combo['values'] = files
            if files:
                self.file_combo.current(0)
            messagebox.showinfo("Success", f"Software is Up~to Date")
            self.log("Connecting to Server...")
            time.sleep(1)
            self.log("Connected to Server ✅")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch files:\n{str(e)}")
    def load_selected_file(self):
        """Load and parse selected Q&A file"""
        filename = self.file_combo.get()
        if not filename:
            return
            
        try:
            raw_url = f"https://raw.githubusercontent.com/{self.github_user}/" \
                    f"{self.repo_name}/main/{filename}"
            response = requests.get(raw_url)
            response.raise_for_status()
            
            self.qa_pairs = self.parse_qa_content(response.text)
            msg = f"Loaded {len(self.qa_pairs)} Q&A pairs from {filename}"
            messagebox.showinfo("Loaded", msg)
            self.start_btn.config(state="normal")
            self.log(f"File loaded: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def parse_qa_content(self, content):
        """Parse Q&A content while preserving code formatting"""
        qa_dict = {}
        entries = re.split(r'\n##\s*\n', content.strip())
        
        for entry in entries:
            lines = entry.split('\n')
            if not lines:
                continue
                
            # Extract question (first non-empty line)
            question = None
            start_idx = 0
            for idx, line in enumerate(lines):
                if line.strip():
                    question = line.strip().lower()
                    start_idx = idx + 1
                    break
                    
            if not question:
                continue
                
            # Preserve original formatting for answer
            answer = '\n'.join(lines[start_idx:]).strip()
            qa_dict[question] = answer
            
        return qa_dict

    def start_monitoring(self):
        """Start clipboard monitoring thread"""
        self.monitoring = True
        self.status_label.config(text="Status: Monitoring...", foreground="green")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        monitor_thread = threading.Thread(target=self.clipboard_monitor, daemon=True)
        monitor_thread.start()

    def stop_monitoring(self):
        """Stop clipboard monitoring"""
        self.monitoring = False
        self.status_label.config(text="Status: Stopped", foreground="red")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def clipboard_monitor(self):
        """Clipboard monitoring loop with exit command"""
        last_question = ""
        while self.monitoring:
            current_content = pyperclip.paste().strip().lower()
            
            # Check for exit command
            if current_content == self.exit_command:
                self.exit_app()
                break
                
            if current_content and current_content != last_question:
                answer = self.qa_pairs.get(current_content, "No answer found")
                pyperclip.copy(answer)
                self.log(f"Question: {current_content}\nAnswer:\n{answer}\n")
                last_question = current_content
                
                time.sleep(5)
                pyperclip.copy("")
                last_question = ""
            
            time.sleep(1)

    def hide_to_tray(self):
        """Minimize to system tray"""
        self.root.withdraw()
        self.tray_icon.run_detached()

    def show_app(self, icon=None, item=None):
        """Restore from system tray"""
        self.tray_icon.stop()
        self.root.deiconify()

    def exit_app(self, icon=None, item=None):
        """Clean exit from system tray"""
        self.monitoring = False
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit(0)

    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ClipboardApp(root)
    app.run()