import time
import logging
import serial
from threading import Lock

# Configure logger for hardware interactions
logger = logging.getLogger(__name__)

class ArduinoDriver:
    """
    Thread-safe, single-instance hardware driver for the Automotive Ethernet Relay Board.
    Handles communication with Arduino firmware via newline-terminated ASCII commands.
    """

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._lock = Lock()  # Prevents thread collisions between UI and Test Manager
        
        self.connect()

    def connect(self):
        """Establishes serial connection and waits for Arduino bootloader auto-reset."""
        with self._lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()

                logger.info(f"Connecting to Arduino hardware on {self.port}...")
                self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                
                # Arduinos automatically reset on DTR connection. Wait 2 seconds for bootloader.
                time.sleep(2.0)
                
                # Flush initial startup text sent by Arduino C++ setup()
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                logger.info(f"Successfully connected to Arduino on {self.port}")

            except serial.SerialException as e:
                logger.error(f"Serial Connection Error on {self.port}: {e}")
                raise SystemExit(f"CRITICAL: Could not open {self.port}. Is the board plugged in?") from e

    def send_command(self, cmd: str) -> str:
        """
        Thread-safe low-level command dispatcher.
        Sends a command string and returns the single-line response from Arduino.
        """
        with self._lock:
            if not self.ser or not self.ser.is_open:
                raise serial.SerialException("Attempted write, but serial port is closed.")

            clean_cmd = cmd.strip()
            formatted_cmd = f"{clean_cmd}\n"
            
            # Send ASCII command
            self.ser.write(formatted_cmd.encode("utf-8"))
            self.ser.flush()
            
            # Small delay for relay coil settling / Arduino execution
            time.sleep(0.05)

            # Read response string back from Arduino
            response = self.ser.readline().decode("utf-8", errors="ignore").strip()
            logger.debug(f"CMD SENT: '{clean_cmd}' | TX RESPONSE: '{response}'")
            return response

    # --- EXPLICIT HARDWARE CONTROL METHODS ---

    def set_normal(self) -> str:
        """Resets all relays to pass-through operational state."""
        return self.send_command("normal")

    def set_fault_open(self) -> str:
        """Injects an Open Circuit condition on TRX lines."""
        return self.send_command("fault-open")

    def set_fault_short(self) -> str:
        """Injects a Short Circuit condition between TRX+ and TRX-."""
        return self.send_command("fault-short")

    def set_swap_polarity(self) -> str:
        """Swaps TRX+ and TRX- differential pairs (Polarity Reversal)."""
        return self.send_command("swap-polarity")

    def set_noise_injection(self, enable: bool = True) -> str:
        """Controls Common-Mode Noise Injection circuit."""
        cmd = "inject-noise" if enable else "normal"
        return self.send_command(cmd)

    def get_board_status(self) -> str:
        """Queries hardware board state from Arduino."""
        return self.send_command("status")

    # --- RESOURCE CLEANUP & CONTEXT MANAGERS ---

    def close(self):
        """Safely resets hardware relays to normal and closes the COM port."""
        with self._lock:
            if self.ser and self.ser.is_open:
                try:
                    logger.info("Resetting relays to normal state before shutdown...")
                    self.ser.write(b"normal\n")
                    time.sleep(0.1)
                except Exception:
                    pass
                finally:
                    self.ser.close()
                    logger.info(f"Port {self.port} closed successfully.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()