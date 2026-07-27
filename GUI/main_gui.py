import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import serial.tools.list_ports
import json
import threading
import time

# Allow this script to run directly from the GUI folder by putting the repo root on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Import automated testing modules
from Automated_Test_Scripts.loop_manager import LoopManager, LoopConfig, TestStatistics
from Automated_Test_Scripts.test_models import TestResult, TestStatus

class EthernetTestFixtureGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Automotive Ethernet Test Fixture Controller")
        self.root.geometry("700x880")
        self.root.resizable(False, True)

        self.ser = None
        self.is_connected = False
        self.loop_manager = None

        self.relay_names = ["ST1", "ST2", "ST3", "ST4", "DT", "DT1", "DT2"]
        self.relay_indicators = {}
        self.relay_buttons = {}
        self.relay_status = [False, False, False, False, False, False, False]
        self.relay_index = {name: idx for idx, name in enumerate(self.relay_names)}

        # Loop Configuration Variables
        self.loop_iters_var = tk.IntVar(value=10)
        self.stop_fail_var = tk.BooleanVar(value=False)
        self.enable_10s_var = tk.BooleanVar(value=True)
        self.enable_100_var = tk.BooleanVar(value=True)
        self.enable_1000_var = tk.BooleanVar(value=True)
        self.enable_multig_var = tk.BooleanVar(value=True)

        self.create_widgets()
        self.refresh_ports()

        # Ensure background threads die when the window is closed
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # 1. Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text=" Serial Connection ", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky="w")
        self.port_cb = ttk.Combobox(conn_frame, width=15, state="readonly")
        self.port_cb.grid(row=0, column=1, padx=5)

        ttk.Button(conn_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        
        self.btn_connect = ttk.Button(conn_frame, text="Connect (Manual)", command=self.toggle_connection)
        self.btn_connect.grid(row=0, column=3, padx=10)

        # 2. Automated Stress Test Dashboard
        loop_frame = ttk.LabelFrame(self.root, text=" Automated Stress Testing Loop ", padding=10)
        loop_frame.pack(fill="x", padx=10, pady=5)

        # Loop Configuration
        config_frame = ttk.Frame(loop_frame)
        config_frame.pack(fill="x", pady=5)
        
        ttk.Label(config_frame, text="Iterations:").grid(row=0, column=0, sticky="w")
        ttk.Entry(config_frame, textvariable=self.loop_iters_var, width=8).grid(row=0, column=1, sticky="w", padx=5)
        
        ttk.Checkbutton(config_frame, text="Stop on First Failure", variable=self.stop_fail_var).grid(row=0, column=2, columnspan=2, padx=15, sticky="w")

        # Test Suite Selection Checkboxes
        ttk.Checkbutton(config_frame, text="10BASE-T1S", variable=self.enable_10s_var).grid(row=1, column=0, sticky="w", pady=(8,0))
        ttk.Checkbutton(config_frame, text="100BASE-T1", variable=self.enable_100_var).grid(row=1, column=1, sticky="w", pady=(8,0), padx=5)
        ttk.Checkbutton(config_frame, text="1000BASE-T1", variable=self.enable_1000_var).grid(row=1, column=2, sticky="w", pady=(8,0), padx=5)
        ttk.Checkbutton(config_frame, text="MultiGBASE-T1", variable=self.enable_multig_var).grid(row=1, column=3, sticky="w", pady=(8,0), padx=5)

        # Loop Controls & Stats
        stats_frame = ttk.Frame(loop_frame)
        stats_frame.pack(fill="x", pady=10)

        self.btn_start_loop = ttk.Button(stats_frame, text="Start Loop", command=self.start_loop)
        self.btn_start_loop.grid(row=0, column=0, padx=5, pady=5)
        
        self.btn_stop_loop = ttk.Button(stats_frame, text="Stop Loop", command=self.stop_loop, state="disabled")
        self.btn_stop_loop.grid(row=0, column=1, padx=5, pady=5)

        self.lbl_cycle = ttk.Label(stats_frame, text="Cycle: 0 / 0", font=("Helvetica", 10, "bold"))
        self.lbl_cycle.grid(row=0, column=2, padx=15)
        
        self.lbl_yield = ttk.Label(stats_frame, text="Yield: 0.0%", font=("Helvetica", 10, "bold"))
        self.lbl_yield.grid(row=0, column=3, padx=15)
        
        self.lbl_passed = ttk.Label(stats_frame, text="Passed: 0", foreground="green")
        self.lbl_passed.grid(row=1, column=2, padx=15, sticky="w")
        
        self.lbl_failed = ttk.Label(stats_frame, text="Failed: 0", foreground="red")
        self.lbl_failed.grid(row=1, column=3, padx=15, sticky="w")

        self.lbl_time = ttk.Label(stats_frame, text="Time: 00:00")
        self.lbl_time.grid(row=1, column=0, columnspan=2)

        # 3. High Level Test Preset Controls (Manual)
        self.cmd_frame = ttk.LabelFrame(self.root, text=" Manual Test Modes ", padding=10)
        self.cmd_frame.pack(fill="x", padx=10, pady=5)

        ttk.Button(self.cmd_frame, text="Normal Passthrough", command=lambda: self.send_command("normal")).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(self.cmd_frame, text="Swap Polarity (IOP_18)", command=lambda: self.send_command("swap-polarity")).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.cmd_frame, text="Inject Open Circuit (IOP_32)", command=lambda: self.send_command("fault-open")).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(self.cmd_frame, text="Inject Short Circuit (IOP_33)", command=lambda: self.send_command("fault-short")).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(self.cmd_frame, text="Enable DT Routing", command=lambda: self.send_command("set-routing 1")).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(self.cmd_frame, text="Disable DT Routing", command=lambda: self.send_command("set-routing 0")).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.cmd_frame.columnconfigure(0, weight=1)
        self.cmd_frame.columnconfigure(1, weight=1)

        # 4. Relay Status Visualization & Manual Control
        relay_frame = ttk.LabelFrame(self.root, text=" Live Relay Status Matrix ", padding=10)
        relay_frame.pack(fill="x", padx=10, pady=5)

        for idx, r_name in enumerate(self.relay_names):
            lbl = tk.Label(
                relay_frame,
                text=r_name,
                width=8,
                relief="ridge",
                bg=self._relay_color(self.relay_status[idx]),
                fg="white",
                font=("Helvetica", 10, "bold")
            )
            lbl.grid(row=0, column=idx, padx=4, pady=5)
            self.relay_indicators[r_name] = lbl

            btn = ttk.Button(
                relay_frame,
                text=self._relay_button_text(self.relay_status[idx]),
                command=lambda r_name=r_name, idx=idx: self.toggle_relay_state(r_name, idx),
                width=9
            )
            btn.grid(row=1, column=idx, padx=4, pady=3)
            self.relay_buttons[r_name] = btn

        ttk.Button(relay_frame, text="Query Board Status", command=lambda: self.send_command("status")).grid(row=2, column=0, columnspan=7, pady=8)

        # 5. Serial Log Console
        log_frame = ttk.LabelFrame(self.root, text=" Console Output ", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_box = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=True)

    # --- Relay Helpers ---
    def _relay_color(self, is_on):
        return "#4CAF50" if is_on else "#f44336"

    def _relay_button_text(self, is_on):
        return "Turn Off" if is_on else "Turn On"

    def _set_indicator_state(self, r_name, is_on):
        self.relay_indicators[r_name].config(bg=self._relay_color(is_on), fg="white")

    def _set_button_state(self, r_name, is_on):
        self.relay_buttons[r_name].config(text=self._relay_button_text(is_on))

    def toggle_relay_state(self, r_name, idx):
        new_state = not self.relay_status[idx]
        confirm = messagebox.askyesno("Confirm Relay Change", f"Switch {r_name} to {'ON' if new_state else 'OFF'}?")
        if confirm:
            self.relay_status[idx] = new_state
            self._set_indicator_state(r_name, new_state)
            self._set_button_state(r_name, new_state)
            self.push_state_to_arduino()
            self.log(f"{r_name} set to {'ON' if new_state else 'OFF'}")

    def push_state_to_arduino(self):
        if not self.is_connected or not self.ser:
            return

        message = "set-config "
        for x in self.relay_status:
            message += "1" if x else "0"
        
        self.send_command(message)

    # --- Manual Connection Management ---
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
                self.btn_connect.config(text="Disconnect (Manual)")
                self.log("Connected manually to " + port)

                self.reader_thread = threading.Thread(target=self.read_serial_loop, daemon=True)
                self.reader_thread.start()

                time.sleep(0.5)
                self.send_command("status")
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))
        else:
            self.is_connected = False
            if self.ser:
                self.ser.close()
            self.btn_connect.config(text="Connect (Manual)")
            self.log("Manual connection closed.")
            self.reset_indicators()

    def send_command(self, cmd):
        if self.is_connected and self.ser:
            try:
                full_cmd = cmd + "\n"
                self.ser.write(full_cmd.encode('utf-8'))
                self.log(f">> {cmd}")
            except Exception as e:
                self.log(f"Send Error: {e}")
        else:
            self.log("Cannot send command: COM port not connected manually.")

    def read_serial_loop(self):
        while self.is_connected and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    self.log(f"<< {line}")
                    self.parse_line(line)
            except Exception:
                break

    # --- Automated Loop Management ---
    def start_loop(self):
        port = self.port_cb.get()
        if not port:
            messagebox.showerror("Error", "No COM port selected.")
            return

        if self.is_connected:
            self.log("Releasing manual COM port lock for Automated Loop...")
            self.toggle_connection()

        config = LoopConfig(
            iterations=self.loop_iters_var.get(),
            stop_on_first_failure=self.stop_fail_var.get(),
            enable_10baset1s=self.enable_10s_var.get(),
            enable_100baset1=self.enable_100_var.get(),
            enable_1000baset1=self.enable_1000_var.get(),
            enable_multigbaset1=self.enable_multig_var.get()
        )

        self.loop_manager = LoopManager(serial_port=port)
        
        # Wire up thread-safe callbacks
        self.loop_manager.on_log = self.on_log_callback
        self.loop_manager.on_progress = self.on_progress_callback
        self.loop_manager.on_complete = self.on_complete_callback

        if not self.loop_manager.initialize_hardware():
            messagebox.showerror("Hardware Error", f"Failed to initialize board on {port}")
            return

        self.btn_start_loop.config(state="disabled")
        self.btn_stop_loop.config(state="normal")
        self.btn_connect.config(state="disabled")

        for child in self.cmd_frame.winfo_children():
            child.configure(state='disabled')

        self.loop_manager.start_loop(config)

    def stop_loop(self):
        if self.loop_manager and self.loop_manager.is_running():
            self.log("Stop requested... waiting for current test to finish.")
            self.loop_manager.stop_loop()
            self.btn_stop_loop.config(state="disabled")

    # --- Thread-Safe UI Update Callbacks ---
    def on_log_callback(self, msg: str):
        self.root.after(0, self.log, msg)

    def on_progress_callback(self, stats: TestStatistics):
        self.root.after(0, self.update_stats_ui, stats)

    def on_complete_callback(self, stats: TestStatistics):
        self.root.after(0, self.handle_loop_complete, stats)

    def update_stats_ui(self, stats: TestStatistics):
        self.lbl_cycle.config(text=f"Cycle: {stats.current_cycle} / {stats.total_cycles_planned}")
        self.lbl_yield.config(text=f"Yield: {stats.pass_yield_percent:.1f}%")
        self.lbl_passed.config(text=f"Passed: {stats.passed_tests}")
        self.lbl_failed.config(text=f"Failed: {stats.failed_tests}")
        
        mins, secs = divmod(int(stats.elapsed_time_sec), 60)
        self.lbl_time.config(text=f"Time: {mins:02d}:{secs:02d}")

    def handle_loop_complete(self, stats: TestStatistics):
        self.log("--- LOOP COMPLETE ---")
        self.log(f"Final Yield: {stats.pass_yield_percent:.1f}%")
        
        self.btn_start_loop.config(state="normal")
        self.btn_stop_loop.config(state="disabled")
        self.btn_connect.config(state="normal")
        
        for child in self.cmd_frame.winfo_children():
            child.configure(state='normal')

    # --- UI Helpers ---
    def parse_line(self, line):
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                self.root.after(0, self.update_indicators, data)
            except json.JSONDecodeError:
                pass

    def update_indicators(self, data):
        """Updates relay status indicators and toggle buttons from board status."""
        for r_name in self.relay_names:
            if r_name in data:
                idx = self.relay_index[r_name]
                is_active = bool(data[r_name])
                self.relay_status[idx] = is_active
                self._set_indicator_state(r_name, is_active)
                self._set_button_state(r_name, is_active)

    def reset_indicators(self):
        """Resets all relay status indicators and buttons back to Off (Red)."""
        for idx, r_name in enumerate(self.relay_names):
            self.relay_status[idx] = False
            self._set_indicator_state(r_name, False)
            self._set_button_state(r_name, False)

    def log(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def on_closing(self):
        if self.loop_manager and self.loop_manager.is_running():
            self.loop_manager.stop_loop()
        if self.is_connected and self.ser:
            self.ser.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = EthernetTestFixtureGUI(root)
    root.mainloop()