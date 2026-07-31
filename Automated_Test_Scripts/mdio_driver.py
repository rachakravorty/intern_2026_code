import logging
import time
import serial

logger = logging.getLogger(__name__)


class MDIODriver:
    """IEEE 802.3 Ethernet PHY MDIO/MDC Register Interface via Arduino USB Bridge."""

    def __init__(
        self,
        phy_addr: int = 1,
        mock: bool = True,
        port: str = "COM3",
        baudrate: int = 115200,
        timeout: float = 1.0,
    ):
        self.phy_addr = phy_addr
        self.mock = mock
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

        self._registers = {
            0x0000: 0x1100,
            0x0001: 0x782D,
            0x0012: 0x0007,
            0x001A: 0x0000,
            0x001C: 0x0000,
        }

        if not self.mock:
            try:
                self.ser = serial.Serial(
                    self.port, self.baudrate, timeout=self.timeout
                )
                # Allow Arduino to reset after serial connection opens
                time.sleep(2.0)
                self.ser.reset_input_buffer()
                logger.info(f"Connected to Arduino MDIO Bridge on {self.port}")
            except serial.SerialException as e:
                logger.error(
                    f"Failed to connect to MDIO bridge on {self.port}: {e}"
                )
                raise

    def close(self):
        """Closes the serial connection if open."""
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _send_cmd(self, command: str) -> str:
        """Sends a serial command to Arduino and reads back the response line."""
        if not self.ser or not self.ser.is_open:
            raise ConnectionError("Serial port is not connected.")

        self.ser.reset_input_buffer()
        cmd_str = f"{command}\n"
        self.ser.write(cmd_str.encode("utf-8"))

        response = self.ser.readline().decode("utf-8").strip()
        if not response:
            raise TimeoutError(f"No response from Arduino for command: {command}")

        return response

    def read_reg(self, reg_addr: int) -> int:
        """Clause 22 Register Read."""
        if self.mock:
            return self._registers.get(reg_addr, 0x0000)

        # Serial Command Format: READ <phy_addr> <reg_addr>
        cmd = f"R {self.phy_addr} {reg_addr}"
        response = self._send_cmd(cmd)

        try:
            # Accepts response formatted as hex (0x1234) or integer string
            return int(response, 0) & 0xFFFF
        except ValueError:
            logger.error(
                f"Invalid read response from Arduino: '{response}' for reg {hex(reg_addr)}"
            )
            return 0x0000

    def write_reg(self, reg_addr: int, value: int):
        """Clause 22 Register Write."""
        if self.mock:
            self._registers[reg_addr] = value & 0xFFFF
            return

        # Serial Command Format: WRITE <phy_addr> <reg_addr> <value>
        cmd = f"W {self.phy_addr} {reg_addr} {value & 0xFFFF}"
        response = self._send_cmd(cmd)

        if "OK" not in response.upper():
            logger.warning(
                f"Write to reg {hex(reg_addr)} received unexpected response: {response}"
            )

    def read_clause45(self, mmd: int, reg: int) -> int:
        """Clause 45 Register Read."""
        if self.mock:
            if mmd == 1 and reg == 1:
                return 0x0004  # Link Up
            if mmd == 3 and reg == 0x0800:
                return 0  # Corrected FEC
            if mmd == 3 and reg == 0x0801:
                return 0  # Uncorrectable FEC
            if mmd == 1 and reg == 0x0900:
                return 9  # Eye margin
            return 0

        # Serial Command Format: R45 <phy_addr> <mmd> <reg_addr>
        cmd = f"R45 {self.phy_addr} {mmd} {reg}"
        response = self._send_cmd(cmd)

        try:
            return int(response, 0) & 0xFFFF
        except ValueError:
            logger.error(
                f"Invalid Clause 45 response: '{response}' for MMD {mmd}, reg {hex(reg)}"
            )
            return 0x0000

    def get_link_status(self) -> bool:
        return bool(self.read_reg(0x01) & (1 << 2))

    def set_mock_link(self, state: bool):
        bmsr = self._registers.get(0x01, 0x7829)
        self._registers[0x01] = (
            (bmsr | (1 << 2)) if state else (bmsr & ~(1 << 2))
        )

    def get_sqi(self) -> int:
        return self.read_reg(0x12) & 0x0007

    def run_tdr(self) -> dict:
        raw = self.read_reg(0x001C)
        fault_code = (raw >> 8) & 0x03
        dist = raw & 0xFF
        fault_map = {0: "OK", 1: "OPEN", 2: "SHORT"}
        return {"status": fault_map.get(fault_code, "OK"), "distance": dist}

    def set_mock_tdr(self, status_str: str, distance_m: int = 5):
        code_map = {"OK": 0, "OPEN": 1, "SHORT": 2}
        code = code_map.get(status_str, 0)
        self._registers[0x001C] = (code << 8) | (distance_m & 0xFF)

    def wait_for_link(self,state: bool,timeout=1.0):

        deadline = time.perf_counter()+timeout

        while time.perf_counter()<deadline:

            if self.get_link_status()==state:
                return True

            time.sleep(.005)

        return False