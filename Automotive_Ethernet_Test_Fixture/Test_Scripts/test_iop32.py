from Controllers.arduino_controller import ArduinoController
from Controllers.mdio_controller import MDIOController

class TestIOP32:

    def __init__(self):

        self.arduino = ArduinoController()
        self.mdio = MDIOController()

    def run(self):

        print("===================================")
        print("Running IOP_32")
        print("Open Circuit Diagnostic")
        print("===================================")

        # Connect to hardware
        self.arduino.connect()
        self.mdio.connect()

        # Configure fixture
        self.arduino.open_circuit()

        # Wait for relay to settle
        time.sleep(1)

        # Start cable diagnostics
        self.mdio.start_cable_diagnostics()

        # Read results
        cable_result = self.mdio.read_cable_status()

        if cable_result == "OPEN":

            print("PASS")

            passed = True

        else:

            print("FAIL")

            passed = False

        # Return fixture to normal
        self.arduino.normal_mode()

        return {
            "Test":"IOP_32",
            "Passed":passed,
            "Expected":"OPEN",
            "Actual":cable_result
        }
