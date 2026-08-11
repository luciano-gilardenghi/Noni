class Controller:
    def __init__(self):
        self.gui = None

    def pause_gui(self):
        self.gui.disable_entry()

    def restart_stack(self):
        self.gui.restart_stack()

    def delete_focus(self):
        self.gui.window.set_focus(None)
    def set_gui(self, gui):
        """Let the Controller know about the user interface."""
        self.gui = gui
