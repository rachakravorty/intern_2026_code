class BaseTest:
    def __init__(self, arduino, mdio):
        self.arduino = arduino
        self.mdio = mdio

    def run(self):
        raise NotImplementedError("Each test must implement run().")
