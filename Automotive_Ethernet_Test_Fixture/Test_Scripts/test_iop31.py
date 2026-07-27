from base_test import BaseTest

class TestIOP31(BaseTest):

    def run(self):

        print("Running IOP_31")

        # Configure fixture
        self.arduino.normal()

        # Allow link to stabilize
        # (time delay to be determined from your hardware)
        # time.sleep(...)

        # Read PHY information
        link = self.mdio.read_link_status()
        cable = self.mdio.read_cable_status()
        errors = self.mdio.read_error_flags()

        passed = (
            link and
            cable == "GOOD" and
            errors == 0
        )

        return {
            "test": "IOP_31",
            "passed": passed,
            "link": link,
            "cable": cable,
            "errors": errors
        }
