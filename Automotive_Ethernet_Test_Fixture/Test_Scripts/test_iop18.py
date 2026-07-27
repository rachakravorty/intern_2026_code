import time

class TestIOP18:

    def __init__(self, arduino, mdio):
        self.arduino = arduino
        self.mdio = mdio

    def run(self):

        print("====================================")
        print("Running 100BASET1_IOP_18")
        print("Swapped Polarity Test")
        print("====================================")

        # 1. Configure the fixture
        self.arduino.swap_polarity()

        # 2. Allow relays to settle
        time.sleep(1)

        # 3. Monitor the DUT for 750 ms
        start_time = time.time()
        link_detected = False

        while (time.time() - start_time) < 0.75:

            if self.mdio.read_link_status():
                link_detected = True
                break

            time.sleep(0.01)

        # 4. Optional: Read polarity flag if supported
        polarity_detected = self.mdio.read_polarity_status()

        # 5. Determine PASS/FAIL
        if (not link_detected) or polarity_detected:
            passed = True
        else:
            passed = False

        # 6. Return fixture to normal
        self.arduino.normal_mode()

        # 7. Return results
        return {
            "Test": "100BASET1_IOP_18",
            "Passed": passed,
            "Expected": "Link Down or Polarity Flag Set",
            "LinkDetected": link_detected,
            "PolarityDetected": polarity_detected
        }
