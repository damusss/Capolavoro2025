from src.common import *
from src.lineedicampo_sim import LineeDiCampo_Sim


class SimulationApp(mili.UIApp):
    def __init__(self):
        super().__init__(
            pygame.Window("Simulazione Scenari Fisici", (1200, 800), borderless=True),
            {"start_style": {"default_align": "center"}|mili.PADLESS},
        )
        self.original_title = self.window.title
        self.mili.default_styles(
            text={"sysfont": True, "growx": True, "name": "Segoe UI"}
        )
        mili.icon.setup("appdata", "white")

        self.simulation = None
        self.simulations = [LineeDiCampo_Sim(self)]
        self.simulation = self.simulations[0]
        self.simulation.enter()
        self.simulation.spawn(Charge((0, 0), 2))
        self.simulation.spawn(Charge((30, 20), 0.1))

    def ui(self):
        if self.simulation:
            self.simulation.ui()
        else:
            self.mili.text_element("Simulazioni", {"size": self.scale(40)})

    def event(self, e):
        if self.simulation:
            self.simulation.event(e)

    def update(self):
        if self.simulation:
            self.simulation.update()

    def exit_sim(self):
        self.window.title = self.original_title
        self.simulation = None


if __name__ == "__main__":
    SimulationApp().run()
