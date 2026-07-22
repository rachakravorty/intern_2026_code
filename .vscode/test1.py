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
        self.relay_buttons = {}
        self.relay_status = [True, False, True, False, True, False, True]
        self.relay_index = {name: idx for idx, name in enumerate(self.relay_names)}

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

        ttk.Button(cmd_frame, text="Normal Passthrough", command=self.apply_normal_passthrough).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Swap Polarity (IOP_18)", command=self.apply_swap_polarity).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Inject Open Circuit (IOP_32)", command=self.apply_inverted_circuit).grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Inject Short Circuit (IOP_33)", command=self.apply_short_circuit).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Routing Toggle
        ttk.Button(cmd_frame, text="Short to GND", command=self.apply_short_to_gnd).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        ttk.Button(cmd_frame, text="Short to 12V", command=self.apply_short_to_12v).grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        cmd_frame.columnconfigure(0, weight=1)
        cmd_frame.columnconfigure(1, weight=1)

        # Relay Status Visualization
        relay_frame = ttk.LabelFrame(self.root, text=" Live Relay Status Matrix ", padding=10)
        relay_frame.pack(fill="x", padx=10, pady=5)

        for idx, r_name in enumerate(self.relay_names):
            lbl = tk.Label(relay_frame, text=r_name, width=8, relief="ridge", bg=self._relay_color(self.relay_status[idx]), fg="white", font=("Helvetica", 10, "bold"))
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

    def _push_state_to_arduino(self):
        if not self.is_connected or not self.ser:
            return

        payload = {
            relay_name: bool(self.relay_status[self.relay_index[relay_name]])
            for relay_name in self.relay_names
        }
        message = json.dumps(payload) + "\n"
        try:
            self.ser.write(message.encode('utf-8'))
            self.log(f">> {message.strip()}")
        except Exception as e:
            self.log(f"Send Error: {e}")

    def apply_normal_passthrough(self):
        confirm = messagebox.askyesno("Confirm Normal Passthrough", "Set ST1, ST2, ST3, and ST4 to ON?")
        if not confirm:
            return

        for relay_name in ["ST1", "ST2", "ST3", "ST4"]:
            idx = self.relay_index[relay_name]
            self.relay_status[idx] = True
            self._set_indicator_state(relay_name, True)
            self._set_button_state(relay_name, True)

        self._push_state_to_arduino()
        self.log("Normal passthrough applied: ST1-ST4 ON")

    def apply_swap_polarity(self):
        confirm = messagebox.askyesno("Confirm Swap Polarity", "Invert DT1 and DT2?")
        if not confirm:
            return

        for relay_name in ["DT1", "DT2"]:
            idx = self.relay_index[relay_name]
            new_state = not self.relay_status[idx]
            self.relay_status[idx] = new_state
            self._set_indicator_state(relay_name, new_state)
            self._set_button_state(relay_name, new_state)

        self._push_state_to_arduino()
        self.log("Swap polarity applied: DT1 and DT2 inverted")

    def apply_inverted_circuit(self):
        confirm = messagebox.askyesno("Confirm Open Circuit", "Set ST1, ST2, ST3, and ST4 to OFF?")
        if not confirm:
            return

        for relay_name in ["ST1", "ST2", "ST3", "ST4"]:
            idx = self.relay_index[relay_name]
            self.relay_status[idx] = False
            self._set_indicator_state(relay_name, False)
            self._set_button_state(relay_name, False)

        self._push_state_to_arduino()
        self.log("Open circuit applied: ST1-ST4 OFF")

    def apply_short_circuit(self):
        confirm = messagebox.askyesno("Confirm Short Circuit", "Set ST1 and ST2 to ON and ST3 and ST4 to OFF?")
        if not confirm:
            return

        for relay_name, state in [("ST1", True), ("ST2", True), ("ST3", False), ("ST4", False)]:
            idx = self.relay_index[relay_name]
            self.relay_status[idx] = state
            self._set_indicator_state(relay_name, state)
            self._set_button_state(relay_name, state)

        self._push_state_to_arduino()
        self.log("Short circuit applied: ST1-ST2 ON, ST3-ST4 OFF")

    def apply_short_to_gnd(self):
        confirm = messagebox.askyesno("Confirm Short to GND", "Set DT to ON?")
        if not confirm:
            return

        relay_name = "DT"
        idx = self.relay_index[relay_name]
        self.relay_status[idx] = True
        self._set_indicator_state(relay_name, True)
        self._set_button_state(relay_name, True)

        self._push_state_to_arduino()
        self.log("Short to GND applied: DT ON")

    def apply_short_to_12v(self):
        confirm = messagebox.askyesno("Confirm Short to 12V", "Set DT to OFF?")
        if not confirm:
            return

        relay_name = "DT"
        idx = self.relay_index[relay_name]
        self.relay_status[idx] = False
        self._set_indicator_state(relay_name, False)
        self._set_button_state(relay_name, False)

        self._push_state_to_arduino()
        self.log("Short to 12V applied: DT OFF")

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

    def _relay_color(self, is_on):
        return "#4CAF50" if is_on else "#F44336"

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
            self._push_state_to_arduino()
            self.log(f"{r_name} set to {'ON' if new_state else 'OFF'}")

    def update_indicators(self, data):
        for r_name in self.relay_names:
            if r_name in data:
                self.relay_status[self.relay_index[r_name]] = bool(data[r_name])
                self._set_indicator_state(r_name, self.relay_status[self.relay_index[r_name]])
                self._set_button_state(r_name, self.relay_status[self.relay_index[r_name]])

    def reset_indicators(self):
        for idx, r_name in enumerate(self.relay_names):
            self.relay_status[idx] = False
            self._set_indicator_state(r_name, False)
            self._set_button_state(r_name, False)

    def log(self, text):
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = EthernetTestFixtureGUI(root)
    root.mainloop()