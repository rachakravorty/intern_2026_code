
from base_test import BaseTest

class TestIOP18(BaseTest):

    def run(self):

        print("Running IOP_18")

        self.arduino.polarity()

        # Wait for DUT to react
        # time.sleep(...)

        link = self.mdio.read_link_status()

        polarity = self.mdio.read_polarity_status()

        passed = (
            (not link) and
            polarity
        )

        self.arduino.normal()

        return {
            "test": "IOP_18",
            "passed": passed,
            "link": link,
            "polarity_detected": polarity
        }
