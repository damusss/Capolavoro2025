import pygame
import mili
import typing

if typing.TYPE_CHECKING:
    from main import SimulationApp


K0 = 8.85e-12
CU = 1.6e-19


class Entity:
    def __init__(self, pos=(0, 0), label="", value=0):
        self.pos = pygame.Vector2(pos)
        self.screen_center = pygame.Vector2()
        self.label = label
        self.value = value

    def update(self, camera: "Camera"): ...

    def draw(self, canva: pygame.Surface): ...


class CircleEntity(Entity):
    def __init__(self, pos=(0, 0), radius=1, color="white", label="", value=0):
        super().__init__(pos, label, value)
        self.radius = radius
        self.screen_center = pygame.Vector2()
        self.screen_r = 0
        self.screen_box = pygame.FRect()
        self.color = color

    def update(self, cam: "Camera"):
        self.screen_center = cam.transform_pos(self)
        self.screen_r = cam.transform_size(self.radius)
        self.screen_box = pygame.FRect(
            0, 0, self.screen_r * 2, self.screen_r * 2
        ).move_to(center=self.screen_center)

    def draw(self, canva: pygame.Surface):
        pygame.draw.circle(canva, self.color, self.screen_center, self.screen_r)


class Charge(CircleEntity):
    def __init__(self, pos=(0, 0), value=0):
        super().__init__(pos, 1, "white", "", value)
        self.refresh()
        self.highest_field = K0*CU*self.value

    def refresh(self):
        if self.value > 0:
            self.label = "+"
            self.color = "blue"
        elif self.value < 0:
            self.label = "-"
            self.color = "red"
        else:
            self.label = "N"
            self.color = "white"

    def update(self, cam):
        super().update(cam)
        self.refresh()


class Camera:
    def __init__(self):
        self.pos = pygame.Vector2()
        self.view = pygame.Vector2()
        self.scale = 1
        self.unit_pixels = 100

    @property
    def unit(self):
        return self.unit_pixels * self.scale

    def transform_pos(self, entity: Entity):
        return self.view / 2 + entity.pos*self.unit - (self.pos * self.unit)

    def transform_size(self, size):
        return size * self.unit
    
    def screen_to_world(self, pos: pygame.Vector2):
        return (pos-self.view/2)/self.unit+self.pos*self.unit

    def update(self, scaler: mili.AdaptiveUIScaler):
        self.unit_pixels = scaler.scale(10)


class Simulation:
    name = "None"
    clear_color = "black"

    def __init__(self, app: "SimulationApp"):
        self.app = app
        self.mili = self.app.mili
        self.camera = Camera()
        self.entities: list[Entity] = []
        self.canva = pygame.Surface((10, 10))
        self.init()

    def spawn(self, entity):
        self.entities.append(entity)

    def init(self): ...

    def event(self, e):
        if e.type == pygame.MOUSEWHEEL:
            self.camera.scale += e.y*0.01

    def update(self):
        self.camera.update(self.app.adaptive_scaler)
        for e in self.entities:
            e.update(self.camera)

    def draw(self): ...

    def draw_entities(self):
        labels = []
        for e in self.entities:
            e.draw(self.canva)
            if e.label:
                labels.append((e.label, e.screen_center))
        return labels

    def ui(self):
        with self.mili.begin(None, mili.FILL) as canva:
            self.camera.view = pygame.Vector2(canva.data.rect.size)
            if self.canva.size != self.camera.view:
                self.canva = pygame.Surface(self.camera.view)
            self.canva.fill(self.clear_color)
            self.draw()
            labels = self.draw_entities()
            self.mili.image(self.canva, {"ready": True})
            for label, center in labels:
                style = {"size": self.app.scale(20)}
                size = self.mili.text_size(label, style)
                self.mili.text_element(
                    label,
                    style,
                    pygame.Rect(((0, 0), size)).move_to(center=center),
                    {"ignore_grid": True},
                )

    def enter(self):
        self.app.window.title = f"Simulazione in Corso: {self.name}"
