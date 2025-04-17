from src.common import *
import math

class LineeDiCampo_Sim(Simulation):
    name = "Linee Di Campo"

    def init(self):
        ...

    def update(self):
        print(self.app.clock.get_fps())
        super().update()
        
    def get_field(self, entity: Charge, world: pygame.Vector2):
        dist = entity.pos-world
        dir = dist.normalize()*(-math.copysign(1, entity.value))
        return dir*((K0*entity.value*CU)/(dist.magnitude_squared()))
        
    def draw(self):
        step = 8
        
        for sx in range(0, int(self.camera.view.x), step):
            for sy in range(0, int(self.camera.view.y), step):
                sp = pygame.Vector2(sx, sy)
                world = self.camera.screen_to_world(sp)
                field = pygame.Vector2()
                highest = 0
                for entity in self.entities:
                    entity: Charge
                    if entity.highest_field > highest:
                        highest = entity.highest_field
                    field += self.get_field(entity, world)
                mag = field.magnitude()
                col = ((mag/highest)**0.4)*255
                pygame.draw.rect(self.canva, (0, 0, pygame.math.clamp(col, 0, 255)), (sx, sy, step, step),)
