import time
import serial
import random

class TestBench100BASET1:
    def __init__(self, serial_port="COM3"):
        self.ser = serial.Serial(serial_port, 115200, timeout=1)
        time.sleep(2)

    def set_relays(self, command: str):
        """Sends relay configuration to Arduino PCB."""
        self.ser.write(f"{command}\n".encode("utf-8"))
        time.sleep(0.1)

    # --- MOCKED DUT STATUS (RANDOM 50/50 OUTPUTS) ---
    def get_link_status(self) -> bool:
        """Simulates Link Status with a random 50/50 result."""
        return random.choice([True, False])

    def get_sqi(self) -> int:
        """Simulates SQI reading (0-7)."""
        return random.randint(0, 7)

    def trigger_tdr(self) -> dict:
        """Simulates Cable Diagnostics TDR output."""
        fault_type = random.choice(["SHORT", "OPEN", "OK"])
        return {"status": fault_type}

    # --- TEST CASES ---
    def test_iop_31_baseline(self):
        """100BASET1_IOP_31: Error-Free Channel Baseline"""
        self.set_relays("normal")
        time.sleep(0.5)
        
        status = self.get_link_status()
        sqi = self.get_sqi()
        print(f"[MOCK] Link Status: {status}, SQI: {sqi}")
        
        assert status, "FAIL: Link is down on normal channel"
        assert sqi >= 5, f"FAIL: SQI ({sqi}) is below nominal baseline threshold"
        print("[PASS] IOP_31: Baseline Channel Clear")

    def test_iop_18_swapped_polarity(self):
        """100BASET1_IOP_18: Swapped Polarity Analysis"""
        self.set_relays("swap-polarity")
        start_time = time.time()
        
        # Verify link remains down for >= 750ms
        while time.time() - start_time < 0.8:
            if self.get_link_status():
                self.set_relays("normal")
                raise AssertionError("FAIL: Link established under inverted polarity")
            time.sleep(0.05)
            
        self.set_relays("normal")
        print("[PASS] IOP_18: Swapped Polarity Handled Correctly")

    def test_iop_32_open_circuit(self):
        """100BASET1_IOP_32: Open Circuit Fault Detection"""
        self.set_relays("fault-open")
        diag = self.trigger_tdr()
        self.set_relays("normal")
        
        print(f"[MOCK] TDR Result: {diag['status']}")
        assert diag["status"] == "OPEN", f"FAIL: Expected OPEN fault, got {diag['status']}"
        print("[PASS] IOP_32: Open Circuit Detected")

    def test_iop_33_short_circuit(self):
        """100BASET1_IOP_33: Short Circuit Fault Detection"""
        self.set_relays("fault-short")
        diag = self.trigger_tdr()
        self.set_relays("normal")
        
        print(f"[MOCK] TDR Result: {diag['status']}")
        assert diag["status"] == "SHORT", f"FAIL: Expected SHORT fault, got {diag['status']}"
        print("[PASS] IOP_33: Short Circuit Detected")

    def test_iop_19_revoke_link_status(self):
        """100BASET1_IOP_19: Revoke of Link Status <= 5ms"""
        self.set_relays("normal")
        time.sleep(0.2)
        
        t_reset = time.time()
        print("[MOCK] Resetting Link Partner...")
        
        link_dropped = False
        while (time.time() - t_reset) <= 0.005:  # 5ms hard limit
            if not self.get_link_status():
                link_dropped = True
                break
                
        assert link_dropped, "FAIL: Link status not revoked within 5ms"
        print("[PASS] IOP_19: Link Revoked within <= 5ms")


if __name__ == "__main__":
    tb = TestBench100BASET1()
    try:
        tb.test_iop_31_baseline()
        tb.test_iop_18_swapped_polarity()
        tb.test_iop_32_open_circuit()
        tb.test_iop_33_short_circuit()
        tb.test_iop_19_revoke_link_status()
    except AssertionError as e:
        print(e)