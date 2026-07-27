import time
import logging
import serial
from threading import Lock

logger = logging.getLogger(__name__)

class ArduinoDriver:
    """Thread-safe driver for Automotive Ethernet Relay Board."""

    def __init__(self, port: str = "COM3", baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._lock = Lock()
        self.connect()

    def connect(self):
        with self._lock:
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()

                logger.info(f"Connecting to Arduino hardware on {self.port}...")
                self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
                time.sleep(2.0)  # Wait for bootloader reset
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                logger.info(f"Connected to Arduino on {self.port}")

            except serial.SerialException as e:
                logger.error(f"Serial Error on {self.port}: {e}")
                # FIX: Raised RuntimeError instead of SystemExit so GUI doesn't crash
                raise RuntimeError(f"Could not open {self.port}. Verify hardware connection.") from e

    def send_command(self, cmd: str) -> str:
        with self._lock:
            if not self.ser or not self.ser.is_open:
                raise serial.SerialException("Serial port is closed.")

            clean_cmd = f"{cmd.strip()}\n"
            self.ser.write(clean_cmd.encode("utf-8"))
            self.ser.flush()
            time.sleep(0.05)
            return self.ser.readline().decode("utf-8", errors="ignore").strip()

    def set_normal(self) -> str: return self.send_command("normal")
    def set_fault_open(self) -> str: return self.send_command("fault-open")
    def set_fault_short(self) -> str: return self.send_command("fault-short")
    def set_swap_polarity(self) -> str: return self.send_command("swap-polarity")

    def close(self):
        with self._lock:
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write(b"normal\n")
                    time.sleep(0.1)
                except Exception:
                    pass
                finally:
                    self.ser.close()

    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): self.close()