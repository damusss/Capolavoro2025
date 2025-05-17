from src.common import *
from src.bridge import UserData, UserExpression, PlotData
import faulthandler
import random

faulthandler.enable()

# UI for variables
# draw in a concurrent thread


class MathGraphCapolavoro2025(mili.UIApp):
    def __init__(self):
        super().__init__(
            pygame.Window("Loading...", (1200, 800), borderless=True),
            {
                "start_style": mili.PADLESS | mili.X | mili.SPACELESS,
                "target_framerate": 120,
            },
        )
        if SARDINIA:
            self.win_behavior.taskbar_size = 48
        self.original_title = self.window.title
        self.mili.default_styles(
            text={"sysfont": True, "growx": True, "name": "Segoe UI"},
            rect={"border_radius": 0},
            image={"smoothscale": True},
        )
        mili.icon.setup("appdata", "white")
        pygame.key.set_repeat(300, 80)
        self.screen = pygame.Surface((10, 10), pygame.SRCALPHA)
        self.overlay_screen = pygame.Surface((10, 10), pygame.SRCALPHA)
        self.view_rect = pygame.Rect()
        self.dragging = False
        self.data = UserData()
        self.data.view = pygame.Vector2(self.screen.size)
        self.panel_scroll = mili.Scroll("panel_scroll")
        self.panel_rect = pygame.Rect()
        self.panel_dragger = mili.Dragger(
            (self.data.panel_percentage, 0),
            False,
            True,
            "panel_dragger",
        )
        self.precision_slider = mili.Slider.from_axis(
            "x",
            {
                "area_update_id": "precision_a",
                "handle_update_id": "precision_h",
                "handle_size": (10, 10),
            },
        )
        self.fps_slider = mili.Slider.from_axis(
            "x",
            {
                "area_update_id": "fps_a",
                "handle_update_id": "fps_h",
                "handle_size": (10, 10),
            },
        )
        self.precision_slider.valuex = self.steps_to_slider(
            PRECISION_STEPS, self.data.precision
        )
        self.fps_slider.valuex = self.steps_to_slider(FPS_STEPS, self.data.framerate)
        self.show_settings = False
        self.settings_rect = pygame.Rect()
        self.settings_btn_rect = pygame.Rect()
        self.on_quit = self.data.save
        self.win_behavior.maximize()

    def slider_to_value(self, steps, svalue):
        log_steps = numpy.log(steps)
        positions = numpy.linspace(0, 1, len(steps))
        interpolated_log_value = numpy.interp(svalue, positions, log_steps)
        return numpy.exp(interpolated_log_value)

    def steps_to_slider(self, steps, value):
        log_steps = numpy.log(steps)
        positions = numpy.linspace(0, 1, len(steps))
        log_value = numpy.log(value)
        return numpy.interp(log_value, log_steps, positions)

    def ui(self):
        pr = self.mili.current_parent_interaction.data.rect
        pid = self.mili.current_parent_id
        if pr.w == 0:
            return
        with self.mili.begin(
            None,
            {
                "fillx": str((self.data.panel_percentage / pr.w) * 100),
                "filly": True,
                "pad": 0,
                "spacing": 0,
                "update_id": "panel_scroll",
            },
        ) as parent_cont:
            self.panel_rect = parent_cont.data.absolute_rect
            self.mili.rect(mili.style.color(BG))
            self.ui_panel()
        lw = 2
        line = self.mili.element(
            (self.panel_dragger.position, (lw, pr.h)),
            {"ignore_grid": True, "z": 100, "update_id": "panel_dragger"},
        )
        self.mili.vline({"size": lw, "color": mili.style.cond_value(line, *BTNS)})
        self.data.panel_percentage = self.panel_dragger.position.x
        mili.InteractionCursor.update(
            line,
            hover_cursor=pygame.SYSTEM_CURSOR_SIZEWE,
            press_cursor=pygame.SYSTEM_CURSOR_SIZEWE,
        )
        self.mili.element((0, 0, lw, 0))
        self.ui_view()
        if self.show_settings:
            self.ui_settings(pid)

    def ui_settings(self, pid):
        with self.mili.begin(
            pygame.Rect(0, 0, self.data.view.x / 2, self.scale(100)).move_to(
                bottomleft=(self.panel_rect.w + 2, self.panel_rect.h)
            ),
            {"ignore_grid": True, "z": 999999, "parent_id": pid},
        ) as settings_cont:
            self.settings_rect = settings_cont.data.absolute_rect
            self.mili.rect(mili.style.color(BG))
            self.mili.rect(mili.style.outline(BTNS[0]))
            hs = self.scale(20)
            ts = self.scale(17)
            asz = self.scale(10)
            for attrname, steps, slider, replot in [
                ("precision", PRECISION_STEPS, self.precision_slider, True),
                ("framerate", FPS_STEPS, self.fps_slider, False),
            ]:
                slider.style["handle_size"] = (hs, hs)
                with self.mili.begin(
                    None,
                    {
                        "fillx": True,
                        "filly": True,
                        "axis": "x",
                        "default_align": "center",
                    },
                ):
                    self.mili.text_element(
                        f"{attrname.title()}:",
                        {"size": ts, "growx": False},
                        None,
                        {"fillx": "25"},
                    )
                    with self.mili.push_styles(rect={"border_radius": "50"}):
                        with self.mili.begin(
                            (0, 0, 0, asz), slider.area_style | {"fillx": "55"}
                        ):
                            self.mili.rect(mili.style.color(LBG))
                            self.mili.rect(
                                mili.style.outline(BTNS[0]) | {"draw_above": False}
                            )
                            with self.mili.element(
                                slider.handle_rect,
                                slider.handle_style
                                | {
                                    "update_id": [
                                        slider.style["handle_update_id"],
                                        "cursor",
                                    ]
                                },
                            ) as btn:
                                self.mili.rect(
                                    mili.style.color(mili.style.cond_value(btn, *BTNS))
                                )
                                self.mili.rect(mili.style.outline(BTNS[1]))
                    setattr(
                        self.data,
                        attrname,
                        int(self.slider_to_value(steps, slider.valuex)),
                    )
                    if slider.moved and replot:
                        self.data.need_to_plot = True
                    self.mili.text_element(
                        f"{getattr(self.data, attrname)}",
                        {"size": ts, "growx": False},
                        None,
                        {"fillx": "20"},
                    )

    def ui_expr_dashed_line(self):
        l1 = self.mili.hline_element(
            {"size": 1, "color": LBG},
            (0, 0, 0, 1),
            {"fillx": True, "offset": self.panel_scroll.get_offset()},
        )
        self.mili.hline_element(
            {
                "size": 1,
                "dash_size": (self.data.panel_percentage) / 23,
                "color": BTNS[0],
            },
            (
                pygame.Vector2(l1.data.rect.topleft) + self.panel_scroll.get_offset(),
                (l1.data.rect.w, 1),
            ),
            {"ignore_grid": True, "z": 999},
        )

    def ui_expr_visibility(self, expression: UserExpression):
        with self.mili.element(None, mili.FILL | {"update_id": "cursor"}) as btn:
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(
                mili.icon.get_google(
                    "visibility_off" if expression.hidden else "visibility"
                ),
                {"alpha": alpha},
            )
            if btn.left_clicked:
                expression.hidden = not expression.hidden
                self.data.need_to_plot = True

    def ui_expr_derivative(self, expression: UserExpression):
        with self.mili.element(None, mili.FILL | {"update_id": "cursor"}) as btn:
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(
                mili.icon.get_iconify(
                    "math-function"
                    if expression.show_derivative
                    else "math-function-off",
                    "tabler",
                ),
                {"alpha": alpha},
            )
            if btn.left_clicked:
                expression.show_derivative = not expression.show_derivative
                if expression.show_derivative and len(expression.derivatives) <= 0:
                    expression.compute_derivative(self.data)
                self.data.need_to_plot = True

    def ui_expr_area(self, expression: UserExpression):
        with self.mili.element(None, mili.FILL | {"update_id": "cursor"}) as btn:
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(
                mili.icon.get_svg("monitoring")
                if expression.show_area
                else mili.icon.get_google("show_chart"),
                {"alpha": alpha},
            )
            if btn.left_clicked:
                expression.show_area = not expression.show_area
                self.data.need_to_plot = True

    def ui_expr_color(self, expression: UserExpression):
        with self.mili.element(None, mili.FILL | {"update_id": "cursor"}) as btn:
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(
                mili.icon.get_google("palette", expression.color),
                {"alpha": alpha},
            )

    def ui_expr_delete(self, expression):
        with self.mili.element(None, mili.FILL | {"update_id": "cursor"}) as btn:
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(
                mili.icon.get_google("delete"),
                {"alpha": alpha},
            )
            if btn.left_clicked:
                self.data.expressions.remove(expression)
                self.data.need_to_plot = True

    def ui_expr_expanded(self, expression: UserExpression, h):
        self.ui_expr_dashed_line()
        if expression.show_derivative:
            txt = ""
            col = "white"
            size = 15
            if expression.derivative_error:
                txt = expression.derivative_error_reason
                col = "red"
                size = 14
            elif expression.error:
                txt = "Unknown since the expression contains errors"
                col = "red"
                size = 14
            else:
                txts = []
                for derivative in expression.derivatives:
                    if isinstance(derivative, dict):
                        left = sympy.sstr(derivative["left"])
                        right = sympy.sstr(derivative["right"])
                        par = sympy.sstr(derivative["inside"])
                        res = (
                            f"{left} "
                            + "{"
                            + f"{par} >= 0"
                            + "}"
                            + f"\n    {right} "
                            + "{"
                            + f"{par} < 0"
                            + "}"
                        )
                    else:
                        res = sympy.sstr(derivative)
                    txts.append(res)
                txt = ",\n    ".join(txts).replace("**", "^")
            with self.mili.element(
                None, {"fillx": True, "offset": self.panel_scroll.get_offset()}
            ):
                self.mili.rect(mili.style.color(LBG))
                self.mili.text(
                    f"f': {txt}",
                    {
                        "size": self.scale(size),
                        "color": col,
                        "slow_grow": True,
                        "wraplen": self.data.panel_percentage,
                        "align": "left",
                        "font_align": pygame.FONT_LEFT,
                    },
                )
        ch = h / 1.2
        with self.mili.begin(
            (0, 0, 0, ch),
            {
                "fillx": True,
                "axis": "x",
                "pad": 1,
                "offset": self.panel_scroll.get_offset(),
            },
        ):
            self.mili.rect(mili.style.color(LBG))
            self.ui_expr_visibility(expression)
            self.ui_expr_derivative(expression)
            self.ui_expr_area(expression)
            self.ui_expr_color(expression)
            self.ui_expr_delete(expression)

    def ui_panel(self):
        h = self.scale(30)
        self.mili.hline_element(
            {"color": BTNS[0]},
            (0, 0, 0, 1),
            {"fillx": True, "offset": self.panel_scroll.get_offset()},
        )
        rpressed = pygame.mouse.get_just_pressed()[pygame.BUTTON_RIGHT - 1]
        for expression in list(self.data.expressions):
            with self.mili.begin(
                (0, 0, 0, h),
                {
                    "fillx": True,
                    "axis": "x",
                    "spacing": 0,
                    "pad": 0,
                    "offset": self.panel_scroll.get_offset(),
                },
            ) as expr_parent:
                if expr_parent.absolute_hover and rpressed:
                    expression.collapsed = not expression.collapsed
                self.mili.rect(mili.style.color(LBG))
                with self.mili.begin(
                    (0, 0, 0, h),
                    {"fillx": True, "axis": "x"},
                ) as cont:
                    mili.InteractionCursor.update(
                        cont,
                        hover_cursor=pygame.SYSTEM_CURSOR_IBEAM,
                        press_cursor=pygame.SYSTEM_CURSOR_IBEAM,
                    )
                    expression.entry.ui(cont)
                    txt = expression.entry.text
                    expression.edit(txt)
                    expression.check_edit(self.data)
                    expression.entry.style["text_style"]["size"] = self.scale(
                        ENTRY_TSIZE
                    )
                with self.mili.element((0, 0, h, h), {"update_id": "cursor"}) as btn:
                    self.mili.image(
                        mili.icon.get_google(
                            "arrow_drop_down"
                            if expression.collapsed
                            else "arrow_drop_up"
                        ),
                        {"alpha": mili.style.cond_value(btn, *ALPHAS)},
                    )
                    if btn.left_clicked:
                        expression.collapsed = not expression.collapsed
            if not expression.collapsed:
                self.ui_expr_expanded(expression, h)
            if expression.error:
                with self.mili.element(
                    None, {"offset": self.panel_scroll.get_offset()}
                ):
                    self.mili.rect(mili.style.color(LBG))
                    self.mili.text(
                        expression.error_reason,
                        {
                            "size": self.scale(14),
                            "color": "yellow",
                            "slow_grow": True,
                            "wraplen": self.data.panel_percentage,
                        },
                    )

            self.mili.hline_element(
                {"color": BTNS[0]},
                (0, 0, 0, 1),
                {"fillx": True, "offset": self.panel_scroll.get_offset()},
            )
        self.ui_panel_add(h)
        self.ui_panel_settings()
        self.ui_panel_reset()

    def ui_panel_settings(self):
        s = self.scale(40)
        pad = self.scale(3)
        with self.mili.element(
            pygame.Rect(0, 0, s, s).move_to(
                bottomright=(self.panel_rect.w - pad, self.panel_rect.h - pad)
            ),
            {"ignore_grid": True, "z": 999999, "update_id": "cursor"},
        ) as btn:
            self.settings_btn_rect = btn.data.absolute_rect
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(mili.icon.get_google("settings"), {"alpha": alpha})
            if btn.left_clicked:
                self.show_settings = not self.show_settings

    def ui_panel_reset(self):
        s = self.scale(40)
        pad = self.scale(3)
        with self.mili.element(
            pygame.Rect(0, 0, s, s).move_to(
                bottomright=(self.panel_rect.w - pad * 2 - s, self.panel_rect.h - pad)
            ),
            {"ignore_grid": True, "z": 999999, "update_id": "cursor"},
        ) as btn:
            alpha = mili.style.cond_value(btn, *ALPHAS)
            self.mili.image(mili.icon.get_svg("reset_cam"), {"alpha": alpha})
            if btn.left_clicked:
                self.data.reset_cam()

    def ui_panel_add(self, h):
        with self.mili.begin(
            (0, 0, 0, h),
            {
                "fillx": True,
                "anchor": "center",
                "axis": "x",
                "spacing": self.scale(10),
                "offset": self.panel_scroll.get_offset(),
            },
        ):
            with self.mili.begin((0, 0, h, h), {"update_id": "cursor"}) as btn:
                self.mili.image(
                    mili.icon.get_google("add"),
                    {"alpha": mili.style.cond_value(btn, *ALPHAS)},
                )
                if btn.left_clicked:
                    self.data.expressions.append(UserExpression("", self.random_col()))
            with self.mili.begin((0, 0, h, h), {"update_id": "cursor"}) as btn:
                self.mili.image(
                    mili.icon.get_svg("variable_add"),
                    {"alpha": mili.style.cond_value(btn, *ALPHAS)},
                )

    def random_col(self):
        ra, rb = 150, 255
        return (random.randint(ra, rb), random.randint(ra, rb), random.randint(ra, rb))

    def ui_view(self):
        self.mili.id_checkpoint(20000)
        with self.mili.element(
            None,
            {
                "fillx": str(
                    100
                    - (
                        (
                            self.data.panel_percentage
                            / self.mili.current_parent_interaction.data.rect.w
                        )
                        * 100
                    )
                ),
                "filly": True,
            },
        ) as edata:
            size = edata.data.rect.size
            view_pos = pygame.Vector2(edata.data.absolute_rect.topleft)
            self.view_rect = pygame.Rect(view_pos, size)
            old = self.screen
            if self.screen.size != size:
                self.screen = pygame.Surface(size, pygame.SRCALPHA)
                self.overlay_screen = pygame.Surface(size, pygame.SRCALPHA)
                self.data.need_to_plot = True
            self.mili.image(old, {"ready": True})
            self.mili.image(self.overlay_screen, {"ready": True})

    def event(self, e):
        self.panel_scroll.wheel_event(e, constrain_rect=self.panel_rect)
        for expr in self.data.expressions:
            expr.entry.event(e)
        for var in self.data.variables:
            var.name_entry.event(e)
            var.value_entry.event(e)
        mpos = pygame.Vector2(pygame.mouse.get_pos())
        in_rect = self.view_rect.collidepoint(mpos) and not self.show_settings
        if e.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.show_settings = False
        if (
            e.type == pygame.MOUSEBUTTONDOWN
            and e.button == pygame.BUTTON_LEFT
            and not self.settings_rect.collidepoint(e.pos)
            and self.show_settings
            and not self.settings_btn_rect.collidepoint(e.pos)
        ):
            self.show_settings = False
        if e.type == pygame.MOUSEMOTION and (in_rect or self.dragging):
            if any(e.buttons):
                rel = pygame.Vector2(e.rel)
                rel /= self.data.unit * self.data.czoom
                rel.y *= -1
                self.data.cpos -= rel
                self.data.need_to_plot = True
                self.dragging = True
        if e.type == pygame.MOUSEWHEEL and in_rect:
            mpos = mpos - self.view_rect.topleft
            prev = self.data.screen_to_world(mpos)
            self.data.czoom += (e.y * self.data.czoom) * 0.1
            self.data.czoom = pygame.math.clamp(self.data.czoom, 0.000000001, 100000000)
            new = self.data.screen_to_world(mpos)
            self.data.cpos -= new - prev
            self.data.need_to_plot = True
        if e.type == pygame.KEYDOWN:
            if e.mod & pygame.KMOD_CTRL:
                if e.key == pygame.K_s:
                    self.data.save()
                if e.key == pygame.K_o:
                    self.show_settings = not self.show_settings
                if e.key == pygame.K_r:
                    self.data.reset_cam()

    def update(self):
        new_fs = self.scale(FONT_SIZE)
        self.data.font_pad = self.scale(FONT_SIZE / 5)
        if new_fs != self.data.font_size:
            self.data.font_size = new_fs
            self.data.font = pygame.font.SysFont("Segoe UI", new_fs)
        self.style["target_framerate"] = self.data.framerate
        self.window.title = f"Math Graph ({round(self.clock.get_fps())} FPS)"
        self.data.update(self.screen)
        self.overlay_screen.fill(0)
        mvec = pygame.Vector2(pygame.mouse.get_pos()) - self.view_rect.topleft
        world_mouse = self.data.screen_to_world(mvec)
        if not self.dragging:
            try:
                if self.update_closest_point(mvec):
                    self.update_closest_point_backup(mvec, world_mouse)
            except Exception:
                ...
        for expression in self.data.expressions:
            if expression.should_skip_derivative:
                continue
            self.update_derivative(expression, world_mouse)
        self.overlay_screen.blit(
            self.data.font.render(
                f"Mouse: {self.data.format_number(world_mouse[0])} X, {self.data.format_number(world_mouse[1])} Y",
                True,
                AXIS_COL,
            ),
            (self.data.font_pad, self.data.font_pad),
        )

    def update_derivative(self, expr: UserExpression, world_mouse):
        mouse_coord = world_mouse.x
        if expr.kind == "y":
            mouse_coord = world_mouse.y
        for i, derivative_func in enumerate(expr.derivative_funcs):
            if isinstance(derivative_func, dict):
                yvalue = derivative_func["inside"](mouse_coord, *self.data.vars_values)
                if yvalue >= 0:
                    dfunc = derivative_func["right"]
                else:
                    dfunc = derivative_func["left"]
            else:
                dfunc = derivative_func
            try:
                points, tangent_point, slope, y0 = self.data.get_tangent_points(
                    expr, dfunc, expr.numpy_functions[i], mouse_coord
                )
            except Exception:
                return
            if points is None:
                return
            pygame.draw.aaline(
                self.overlay_screen,
                expr.color,
                self.clamp_view(points[0]),
                self.clamp_view(points[1]),
            )
            name = "y0"
            if expr.kind == "y":
                name = "x0"
            tsurf = self.data.font.render(
                f"m: {self.data.format_number(slope)}\n{name}: {self.data.format_number(y0)}",
                True,
                expr.color,
            )
            self.overlay_screen.blit(
                tsurf,
                tsurf.get_rect(
                    midbottom=(
                        pygame.math.clamp(
                            tangent_point[0],
                            tsurf.width / 2 + self.data.font_pad,
                            self.data.view.x - tsurf.width / 2 - self.data.font_pad,
                        ),
                        pygame.math.clamp(
                            tangent_point[1] - self.data.font_pad,
                            self.data.font_pad + tsurf.height,
                            self.data.view.y - self.data.font_pad,
                        ),
                    )
                ),
            )

    def clamp_view(self, point):
        ra, rb = -1e20, 1e20
        return (
            pygame.math.clamp(point[0], ra, rb),
            pygame.math.clamp(point[1], ra, rb),
        )

    def update_closest_point_backup(self, mvec, world_mouse):
        closest = None
        col = None
        for expression in self.data.expressions:
            if expression.should_skip:
                continue
            for func in expression.numpy_functions:
                with numpy.errstate(divide="ignore", invalid="ignore"):
                    y = func(world_mouse.x, *self.data.vars_values)
                if numpy.isnan(y) or numpy.isinf(y):
                    continue
                wpoint = (world_mouse.x, y)
                spoint = self.data.world_to_screen(wpoint)
                dist = (spoint - mvec).magnitude()
                if dist > HOVER_MAX_DIST:
                    continue
                if closest is None:
                    closest = spoint
                    col = expression.color
                else:
                    if dist < (closest - mvec).magnitude():
                        closest = spoint
                        col = expression.color
        if closest is not None:
            pygame.draw.aacircle(self.overlay_screen, col, closest, 3)
            self.render_closest(closest, col)
            return False
        return True

    def update_closest_point(self, mvec):
        closest = None
        mouse = numpy.fromiter(mvec, numpy.float32)
        col = None
        for expression in reversed(self.data.expressions):
            if expression.should_skip:
                continue
            for plot in expression.plots:
                cpoint = self.data.get_closest_point(plot, mouse)
                if cpoint is None:
                    continue
                cpoint = pygame.Vector2(cpoint[0], cpoint[1])
                dist = (cpoint - mvec).magnitude()
                if dist > HOVER_MAX_DIST:
                    continue
                if closest is None:
                    closest = cpoint
                    col = expression.color
                else:
                    if dist < (closest - mvec).magnitude():
                        closest = cpoint
                        col = expression.color
        if closest is not None:
            pygame.draw.aacircle(self.overlay_screen, col, closest, 3)
            self.render_closest(closest, col)
            return False
        return True

    def render_closest(self, closest, col):
        tsurf = self.data.font.render(
            f"({self.data.format_number(closest[0])}, {self.data.format_number(closest[1])})",
            True,
            col,
        )
        self.overlay_screen.blit(
            tsurf,
            tsurf.get_rect(
                midbottom=(
                    pygame.math.clamp(
                        closest[0],
                        tsurf.width / 2 + self.data.font_pad,
                        self.data.view.x - tsurf.width / 2 - self.data.font_pad,
                    ),
                    pygame.math.clamp(
                        closest[1] - self.data.font_pad,
                        self.data.font_pad + tsurf.height,
                        self.data.view.y - self.data.font_pad,
                    ),
                )
            ),
        )


if __name__ == "__main__":
    MathGraphCapolavoro2025().run()
