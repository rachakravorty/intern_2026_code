import time
from arduino_driver import ArduinoDriver
import random

class TestBench10BASET1S:
    def __init__(self, hw_driver):
        self.hw = hw_driver  # Store the shared ArduinoDriver instance

    def set_relays(self, command: str):
        self.hw.send_command(command)  # Driver handles encoding & locks

    def configure_plca(self, node_id: int, local_node_count: int, burst_count: int):
        """Mock PLCA register writes."""
        print(f"[MOCK] Configured PLCA: Node={node_id}, TotalNodes={local_node_count}, Burst={burst_count}")

    # --- MOCKED DUT STATUS (RANDOM 50/50 OUTPUTS) ---
    def get_plca_status(self) -> bool:
        return True

    def get_comm_status(self) -> bool:
        """Simulates bus communication activity (50/50 result)."""
        return random.choice([True, False])

    # --- TEST CASES ---
    def test_plca_config_and_beacon_sync(self):
        """Verifies PLCA Configuration & Beacon Synchronization"""
        self.set_relays("normal")
        self.configure_plca(node_id=2, local_node_count=8, burst_count=3)
        time.sleep(0.1)
        
        plca_active = self.get_plca_status()
        print(f"[MOCK] PLCA Status Active: {plca_active}")
        
        assert plca_active, "FAIL: PLCA status inactive / failed to sync to BEACON"
        print("[PASS] 10BASE-T1S PLCA Configured & Synced")

    def test_fib10_hard_short(self):
        """FIB10: Hard Short (Eth P to Eth N, 0 Ohms)"""
        self.set_relays("fault-short")
        time.sleep(0.1)
        
        comm_state = self.get_comm_status()
        print(f"[MOCK] Comm State under short: {comm_state}")
        assert not comm_state, "FAIL: Bus communication survived 0-Ohm hard short"
        
        self.set_relays("normal")
        time.sleep(0.1)
        
        comm_restored = self.get_comm_status()
        print(f"[MOCK] Comm State after clearing fault: {comm_restored}")
        assert comm_restored, "FAIL: Communication failed to restore after clearing fault"
        
        print("[PASS] FIB10: Hard Short Communication Drop & Immediate Recovery")

    def test_fib12_hard_open(self):
        """FIB12: Hard Bus Line Open Circuit"""
        self.set_relays("fault-open")
        time.sleep(0.1)
        
        comm_state = self.get_comm_status()
        print(f"[MOCK] Comm State under open circuit: {comm_state}")
        assert not comm_state, "FAIL: Bus communication survived complete line break"
        
        self.set_relays("normal")
        time.sleep(0.1)
        
        comm_restored = self.get_comm_status()
        print(f"[MOCK] Comm State after clearing fault: {comm_restored}")
        assert comm_restored, "FAIL: Communication failed to restore after line reconnection"
        
        print("[PASS] FIB12: Hard Bus Line Open Handled Correctly")


if __name__ == "__main__":
    from arduino_driver import ArduinoDriver

    # Context manager automatically opens and closes port
    with ArduinoDriver(port="COM3") as hw:
        tb = TestBench10BASET1S(hw_driver=hw)
        try:
            tb.test_plca_config_and_beacon_sync()
            tb.test_fib10_hard_short()
            tb.test_fib12_hard_open()
        except AssertionError as e:
            print(f"[TEST FAILED] {e}")

