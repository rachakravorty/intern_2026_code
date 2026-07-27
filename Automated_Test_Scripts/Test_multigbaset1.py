import time
from arduino_driver import ArduinoDriver
import random

class TestBenchMultiGBASET1:
    def __init__(self, hw_driver):
        self.hw = hw_driver  # Store the shared ArduinoDriver instance

    def set_relays(self, command: str):
        self.hw.send_command(command)  # Driver handles encoding & locks

    # --- MOCKED DUT STATUS (RANDOM 50/50 OUTPUTS) ---
    def get_link_status(self) -> bool:
        return True

    def get_ber_count(self) -> int:
        """Simulates BER error count (50/50 chance of 0 or errors)."""
        return random.choice([0, random.randint(1, 100)])

    def test_multigbase_ber_threshold(self):
        """Verifies BER stays < 10^-10 under clean channel operational state."""
        self.set_relays("normal")
        time.sleep(0.5)
        
        status = self.get_link_status()
        errors = self.get_ber_count()
        print(f"[MOCK] Link Status: {status}, BER Count: {errors}")
        
        assert status, "FAIL: Link down"
        assert errors == 0, f"FAIL: Bit Errors detected ({errors}), BER threshold violated"
        print("[PASS] MultiGBASE BER Threshold Verified (< 10^-10)")

    def test_iop_22_lp_reset_25ms_ignore_and_stability(self):
        """
        IOP_22 (MultiGBASE Specific):
        1. Must ignore all link signals for first 25ms following LP reset.
        2. Must recover link in <= 120ms.
        3. Must hold link stable for >= 750ms post-link.
        """
        self.set_relays("normal")
        time.sleep(0.2)
        
        t0 = time.time()
        print("[MOCK] Resetting Link Partner...")
        
        # 1. 25ms Ignore Window Check
        while (time.time() - t0) < 0.025:
            if self.get_link_status():
                raise AssertionError("FAIL: DUT acknowledged link-up during 25ms mandatory ignore window")

        # 2. Re-link timing check (<= 120ms total limit)
        relinked = False
        t_relink = time.time()
        while (time.time() - t0) <= 0.120:
            if self.get_link_status():
                relinked = True
                t_relink = time.time()
                break
                
        assert relinked, "FAIL: MultiGBASE failed to re-link within 120ms limit"

        # 3. 750ms Post-Reset Link Stability Hold Rule
        while (time.time() - t_relink) < 0.750:
            if not self.get_link_status():
                raise AssertionError("FAIL: Link dropped during 750ms mandatory stability hold period")
            time.sleep(0.05)

        print("[PASS] MultiGBASE IOP_22: 25ms Window, 120ms Recovery & 750ms Stability PASSED")


if __name__ == "__main__":
    from arduino_driver import ArduinoDriver

    # Context manager automatically opens and closes port
    with ArduinoDriver(port="COM3") as hw:
        tb = TestBenchMultiGBASET1(hw_driver=hw)
        try:
            tb.test_multigbase_ber_threshold()
            tb.test_iop_22_lp_reset_25ms_ignore_and_stability()
        except AssertionError as e:
            print(f"[TEST FAILED] {e}")

