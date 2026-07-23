import serial
import time

try:
    # Connect to Arduino on COM3
    arduino = serial.Serial("COM3", 9600, timeout=1)

    # Give Arduino time to reset
    time.sleep(2)

    print("Connected to Arduino!")

    # Send command '1' (Normal Mode)
    arduino.write(b'1')

    print("Sent command: 1")

    # Read anything the Arduino sends back
    while arduino.in_waiting:
        print(arduino.readline().decode().strip())

    arduino.close()

except Exception as e:
    print("Error:", e)
