import time

class TestIOP32:

    def __init__(self, arduino, mdio):
        self.arduino = arduino
        self.mdio = mdio

    def run(self):

        self.arduino.open_circuit()

        time.sleep(0.1)

        self.mdio.start_cable_diagnostics()

        result = self.mdio.read_cable_status()

        self.arduino.normal_mode()

        return result == "OPEN"
