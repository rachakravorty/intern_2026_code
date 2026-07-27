import time

class TestIOP18:

    def __init__(self, arduino, mdio):
        self.arduino = arduino
        self.mdio = mdio

    def run(self):

        # Configure relay board
        self.arduino.swap_polarity()

        # Relay settling time
        time.sleep(0.1)

        start = time.time()

        while (time.time() - start) < 0.75:

            if self.mdio.read_link_status():

                self.arduino.normal_mode()
                return False

            time.sleep(0.01)

        self.arduino.normal_mode()
        return True
