import pygame
import mili
import numpy
import sympy
import typing

if typing.TYPE_CHECKING:
    from main import MathGraphCapolavoro2025



SURF = pygame.Surface((10, 10), pygame.SRCALPHA)
BTNS = (40, 40, 40), (60,60,60), (32,32,32)
ALPHAS = 180, 255, 150
BG = (10,10,10)
LBG = (BG[0]+5,)*3
ENTRY_STYLE: mili.typing.EntryLineStyleLike = {
    "bg_rect_style": {"color": (BG[0] + 5,) * 3},
}
ENTRY_TSIZE = 17
HOVER_MAX_DIST = 15
SARDINIA = True
PRECISION_STEPS = [100, 500, 1000, 3000, 10000, 20000, 50000]
FPS_STEPS = [30, 45, 60, 90, 120, 244, 360]
