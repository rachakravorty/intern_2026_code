import tkinter as tk
from tkinter import messagebox
import serial
import time


arduino = None


def connect():
    global arduino

    try:
        arduino = serial.Serial("COM3", 9600, timeout=1)

        # Wait for Arduino reset
        time.sleep(2)

        status.config(
            text="Status: Connected",
            fg="green"
        )

        results.config(
            text="Connected to Arduino on COM3"
        )

    except Exception as e:
        messagebox.showerror(
            "Connection Error",
            str(e)
        )


def normal_mode():
    if arduino:
        arduino.write(b'1')

        status.config(
            text="Normal Mode"
        )

        results.config(
            text="DT Relay ON"
        )

def alternate_mode():
    if arduino:
        arduino.write(b'2')

        status.config(
            text="Alternate Mode"
        )

        results.config(
            text="ST Relay ON"
        )

def polarity_mode():
    if arduino:
        arduino.write(b'3')

        status.config(
            text="Polarity Mode"
        )

        results.config(
            text="DT + POL Relay ON"
        )

def all_off():
    if arduino:
        arduino.write(b'0')

        status.config(
            text="All Outputs Off"
        )

        results.config(
            text="All relays OFF"
        )

def run_test():
    if arduino:
        arduino.write(b't')

        status.config(
            text="Running Test..."
        )

        results.config(
            text="Automatic test sequence started"
        )

def blink_mode():
    if arduino:
        arduino.write(b'b')

        status.config(
            text="Blink Mode"
        )

        results.config(
            text="Blinking relays"
        )


def read_serial():

    if arduino:

        if arduino.in_waiting:

            try:
                msg = arduino.readline().decode().strip()

                if msg:
                    results.config(text=msg)

            except:
                pass

    window.after(100, read_serial)

# ----------------------------
# GUI
# ----------------------------
window = tk.Tk()
window.title("PCB Test Controller")
window.geometry("500x500")

# ----------------------------
# Title
# ----------------------------
title = tk.Label(
    window,
    text="PCB Test Controller",
    font=("Arial", 20, "bold")
)
title.pack(pady=20)

# ----------------------------
# Status
# ----------------------------
status = tk.Label(
    window,
    text="Status: Disconnected",
    font=("Arial", 12),
    fg="red"
)
status.pack(pady=10)

# ----------------------------
# Buttons
# ----------------------------
connect_button = tk.Button(
    window,
    text="Connect",
    width=25,
    command=connect
)
connect_button.pack(pady=5)

normal_button = tk.Button(
    window,
    text="Normal Mode",
    width=25,
    command=normal_mode
)
normal_button.pack(pady=5)

alternate_button = tk.Button(
    window,
    text="Alternate Mode",
    width=25,
    command=alternate_mode
)
alternate_button.pack(pady=5)

polarity_button = tk.Button(
    window,
    text="Polarity Mode",
    width=25,
    command=polarity_mode
)
polarity_button.pack(pady=5)

off_button = tk.Button(
    window,
    text="All Off",
    width=25,
    command=all_off
)
off_button.pack(pady=5)

test_button = tk.Button(
    window,
    text="Run Test",
    width=25,
    command=run_test
)
test_button.pack(pady=5)

blink_button = tk.Button(
    window,
    text="Blink Mode",
    width=25,
    command=blink_mode
)
blink_button.pack(pady=5)


results = tk.Label(
    window,
    text="No messages",
    width=40,
    height=8,
    relief="sunken",
    anchor="nw",
    justify="left",
    font=("Courier New", 10)
)
results.pack(pady=20)


exit_button = tk.Button(
    window,
    text="Exit",
    width=20,
    command=window.destroy
)
exit_button.pack(pady=10)

# Start serial reader
read_serial()

# Run GUI
window.mainloop()