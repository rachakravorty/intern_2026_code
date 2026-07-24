import time
import serial
import random

class TestBench1000BASET1:
    def __init__(self, serial_port="COM3"):
        self.ser = serial.Serial(serial_port, 115200, timeout=1)
        self.disable_autoneg()

    def set_relays(self, command: str):
        self.ser.write(f"{command}\n".encode("utf-8"))
        time.sleep(0.1)

    def disable_autoneg(self):
        """Mock auto-negotiation disable."""
        print("[MOCK] Auto-negotiation disabled on DUT")

    # --- MOCKED DUT STATUS (RANDOM 50/50 OUTPUTS) ---
    def get_link_status(self) -> bool:
        """Simulates Link Status with a random 50/50 result."""
        return random.choice([True, False])

    def run_tdr_with_distance(self) -> dict:
        """Simulates High-Speed TDR Status and Fault Location."""
        fault_str = random.choice(["OPEN", "SHORT", "OK"])
        distance_meters = random.randint(1, 15)
        return {"fault": fault_str, "distance": distance_meters}

    def test_iop_16_link_integrity_frame0(self):
        """IOP_16: First-Frame Zero Packet Loss Verification"""
        self.set_relays("normal")
        
        # Poll mock link status until True
        while not self.get_link_status():
            time.sleep(0.01)
            
        # Simulated packet counter (50/50 chance of 0 or error count)
        rx_counter = random.choice([0, 1])
        print(f"[MOCK] First Received Frame Counter: {rx_counter}")
        
        assert rx_counter == 0, f"FAIL: First received frame counter was {rx_counter}, expected 0"
        print("[PASS] IOP_16: Frame 0 Received with Zero Loss")

    def test_iop_32_gigabit_open_tdr(self):
        """IOP_32: Near/Far End Open Circuit with 1-Meter Accuracy"""
        self.set_relays("fault-open")
        tdr = self.run_tdr_with_distance()
        self.set_relays("normal")
        
        print(f"[MOCK] TDR Fault: {tdr['fault']}, Distance: {tdr['distance']}m")
        assert tdr["fault"] == "OPEN", f"FAIL: Expected OPEN, got {tdr['fault']}"
        assert tdr["distance"] >= 1, f"FAIL: Fault location resolution out of bounds ({tdr['distance']}m)"
        print(f"[PASS] IOP_32: Open Circuit Detected at {tdr['distance']}m")

    def test_iop_33_gigabit_short_tdr(self):
        """IOP_33: Near/Far End Short Circuit with 1-Meter Accuracy"""
        self.set_relays("fault-short")
        tdr = self.run_tdr_with_distance()
        self.set_relays("normal")
        
        print(f"[MOCK] TDR Fault: {tdr['fault']}, Distance: {tdr['distance']}m")
        assert tdr["fault"] == "SHORT", f"FAIL: Expected SHORT, got {tdr['fault']}"
        assert tdr["distance"] >= 1, f"FAIL: Fault location resolution out of bounds ({tdr['distance']}m)"
        print(f"[PASS] IOP_33: Short Circuit Detected at {tdr['distance']}m")

    def test_iop_21_dut_reset_recovery(self):
        """IOP_21: DUT Reset Recovery Timing <= 100ms"""
        self.set_relays("normal")
        
        print("[MOCK] Soft resetting DUT...")
        time.sleep(0.02) # 20ms configuration window
        
        t_start = time.time()
        relinked = False
        while (time.time() - t_start) <= 0.100: # 100ms maximum limit
            if self.get_link_status():
                relinked = True
                break
                
        assert relinked, "FAIL: DUT failed to re-establish link within 100ms"
        print("[PASS] IOP_21: DUT Recovered Link in <= 100ms")


if __name__ == "__main__":
    tb = TestBench1000BASET1()
    try:
        tb.test_iop_16_link_integrity_frame0()
        tb.test_iop_32_gigabit_open_tdr()
        tb.test_iop_33_gigabit_short_tdr()
        tb.test_iop_21_dut_reset_recovery()
    except AssertionError as e:
        print(e)