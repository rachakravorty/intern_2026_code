import logging

logger = logging.getLogger(__name__)

class MDIODriver:
    """IEEE 802.3 Ethernet PHY MDIO/MDC Register Interface."""
    def __init__(self, phy_addr: int = 1, mock: bool = True):
        self.phy_addr = phy_addr
        self.mock = mock
        self._registers = {
            0x0000: 0x1100,
            0x0001: 0x782D,
            0x0012: 0x0007,
            0x001A: 0x0000,
            0x001C: 0x0000,
        }

    def read_reg(self, reg_addr: int) -> int:
        if self.mock:
            return self._registers.get(reg_addr, 0x0000)
        raise NotImplementedError("Hardware MDIO bus adapter not connected.")

    def write_reg(self, reg_addr: int, value: int):
        if self.mock:
            self._registers[reg_addr] = value & 0xFFFF
            return
        raise NotImplementedError("Hardware MDIO bus adapter not connected.")

    def get_link_status(self) -> bool:
        return bool(self.read_reg(0x01) & (1 << 2))

    def set_mock_link(self, state: bool):
        bmsr = self._registers.get(0x01, 0x7829)
        self._registers[0x01] = (bmsr | (1 << 2)) if state else (bmsr & ~(1 << 2))

    def get_sqi(self) -> int:
        return self.read_reg(0x12) & 0x0007

    # FIX: Added 'self' parameter to prevent TypeError crash
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