import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import json
import threading
import time

class EthernetTestFixtureGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automotive Ethernet Test Fixture Controller")
        self.root.geometry("620x680")
        self.root.resizable(False, False)

        self.ser = None
        self.is_connected = False

        self.relay_names = ["ST1", "ST2", "ST3", "ST4", "DT", "DT1", "DT2"]
        self.relay_indicators = {}

        self.create_widgets()
        self.refresh_ports()

    def create_widgets(self):
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text=" Serial Connection ", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky="w")
        self.port_cb = ttk.Combobox(conn_frame, width=15, state="readonly")
        self.port_cb.grid(row=0, column=1, padx=5)

        ttk.Button(conn_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        
        self.btn_connect = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=3, padx=10)

        # High Level Test Preset Controls
        cmd_frame = ttk.LabelFrame(self.root, text=" Automated Test Modes ", padding=10)
        cmd_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(cmd_frame, text="Normal Passthrough", command=lambda: self.send_command("normal")).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Swap Polarity (IOP_18)", command=lambda: self.send_command("swap-polarity")).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Inject Open Circuit (IOP_32)", command=lambda: self.send_command("fault-open")).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Inject Short Circuit (IOP_33)", command=lambda: self.send_command("fault-short")).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Routing Toggle
        ttk.Button(cmd_frame, text="Enable DT Routing (HIGH)", command=lambda: self.send_command("set-routing 1")).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Disable DT Routing (LOW)", command=lambda: self.send_command("set-routing 0")).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        cmd_frame.columnconfigure(0, weight=1)
        cmd_frame.columnconfigure(1, weight=1)

        # Relay Status Visualization
        relay_frame = ttk.LabelFrame(self.root, text=" Live Relay Status Matrix ", padding=10)
        relay_frame.pack(fill="x", padx=10, pady=5)

        for idx, r_name in enumerate(self.relay_names):
            lbl = tk.Label(relay_frame, text=r_name, width=8, relief="ridge", bg="#dddddd", font=("Helvetica", 10, "bold"))
            lbl.grid(row=0, column=idx, padx=4, pady=5)
            self.relay_indicators[r_name] = lbl

        ttk.Button(relay_frame, text="Query Board Status", command=lambda: self.send_command("status")).grid(row=1, column=0, columnspan=7, pady=8)

        # Serial Log Console
        log_frame = ttk.LabelFrame(self.root, text=" Serial Console Output ", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_box = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True)

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_cb['values'] = ports
        if ports:
            self.port_cb.current(0)

    def toggle_connection(self):
        if not self.is_connected:
            port = self.port_cb.get()
            if not port:
                messagebox.showerror("Error", "No COM port selected.")
                return
            try:
                self.ser = serial.Serial(port, 115200, timeout=1)
                self.is_connected = True
                self.btn_connect.config(text="Disconnect")
                self.log("Connected to " + port)

                # Read worker thread
                self.reader_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
                self.reader_thread.start()

                # Query initial board status
                time.sleep(0.5)
                self.send_command("status")

            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
        else:
            self.is_connected = False
            if self.ser:
                self.ser.close()
            self.btn_connect.config(text="Connect")
            self.log("Disconnected.")
            self.reset_indicators()

    def send_command(self, cmd):
        if self.is_connected and self.ser:
            try:
                full_cmd = cmd + "\n"
                self.ser.write(full_cmd.encode('utf-8'))
                self.log(f">> {cmd}")
            except Exception as e:
                self.log(f"Send Error: {e}")

    def read_serial_loop(self):
        while self.is_connected and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self.log(f"<< {line}")
                    self.parse_line(line)
            except Exception:
                break

    def parse_line(self, line):
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                self.root.after(0, self.update_indicators, data)
            except json.JSONDecodeError:
                pass

    def update_indicators(self, data):
        for r_name in self.relay_names:
            if r_name in data:
                is_active = bool(data[r_name])
                color = "#4CAF50" if is_active else "#dddddd"
                fg_color = "white" if is_active else "black"
                self.relay_indicators[r_name].config(bg=color, fg=fg_color)

    def reset_indicators(self):
        for lbl in self.relay_indicators.values():
            lbl.config(bg="#dddddd", fg="black")

    def log(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = EthernetTestFixtureGUI(root)
    root.mainloop()