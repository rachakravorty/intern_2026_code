import time

class TestIOP18:

    def __init__(self, arduino, mdio):
        self.arduino = arduino
        self.mdio = mdio

    def run(self):

        print("--------------------------------")
        print("100BASET1_IOP_18")
        print("Swapped Polarity Test")
        print("--------------------------------")

        # Configure relay board
        self.arduino.swap_polarity()

        # Allow relays to settle
        time.sleep(0.1)

        start = time.time()
        link_up = False

        # Monitor for 750 ms
        while (time.time() - start) < 0.75:

            if self.mdio.read_link_status():
                link_up = True
                break

            time.sleep(0.01)

        # Read polarity flag if supported
        polarity_flag = self.mdio.read_polarity_flag()

        # Return relay board to normal
        self.arduino.normal_mode()

        # PASS / FAIL
        if (not link_up) or polarity_flag:

            print("PASS")

            return {
                "Test ID": "100BASET1_IOP_18",
                "Result": True,
                "Expected": "Link Down for >=750ms or Polarity Flag",
                "Link Status": link_up,
                "Polarity Flag": polarity_flag
            }

        else:

            print("FAIL")

            return {
                "Test ID": "100BASET1_IOP_18",
                "Result": False,
                "Expected": "Link Down for >=750ms or Polarity Flag",
                "Link Status": link_up,
                "Polarity Flag": polarity_flag
            }
