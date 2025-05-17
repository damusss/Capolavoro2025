from .common import *
import sympy
import os
import json
import threading


class UserVariable:
    def __init__(self, name="", value=0, vrange=None):
        self.name = name
        self.value = value
        self.vrange = vrange
        self.name_entry = mili.EntryLine(
            self.name,
            ENTRY_STYLE | {"placeholder": "Enter var name...", "characters_limit": 1},
        )
        self.value_entry = mili.EntryLine(
            self.value,
            ENTRY_STYLE | {"placeholder": "Enter number...", "target_number": True},
        )


class PlotData:
    def __init__(self, start, stop, step, variables, cpos, czoom, unit, view):
        self.start = start
        self.stop = stop
        self.step = step
        self.variables = variables
        self.cpos = cpos
        self.cposx, self.cposy = self.cpos
        self.czoom = czoom
        self.unit = unit
        self.view = view
        self.viewx, self.viewy = view


class UserExpression:
    def __init__(self, raw_string="", color="white"):
        self.color = color
        self.raw_string = raw_string
        self.raw_temporary = raw_string
        self.editing = False
        self.edit_start_time = 0
        self.error = False
        self.error_reason = None
        self.plots = []
        self.kind = "x"
        self.computing = False
        self.collapsed = True
        self.hidden = False
        self.show_derivative = False
        self.show_area = False
        self.area_plots = []
        self.derivatives = []
        self.derivative_error = False
        self.derivative_error_reason = False
        self.derivative_funcs = []
        self.numpy_functions = []
        self.solutions = []
        self.parameter = None
        self.entry = mili.EntryLine(
            self.raw_string, ENTRY_STYLE | {"placeholder": "Enter expression..."}
        )

    @property
    def should_skip(self):
        return self.error or self.hidden

    @property
    def should_skip_derivative(self):
        return self.should_skip or self.derivative_error or not self.show_derivative

    def edit(self, new_raw):
        if self.raw_temporary != new_raw:
            self.edit_start_time = pygame.time.get_ticks()
            self.editing = True
        self.raw_temporary = new_raw

    def check_edit(self, data: "UserData"):
        if self.computing:
            return
        if self.editing and pygame.time.get_ticks() - self.edit_start_time >= 500:
            self.raw_string = self.raw_temporary
            self.editing = False
            self.send_compute(data)

    def send_compute(self, data):
        self.computing = True
        thread = threading.Thread(target=self.compute, args=(data,))
        thread.start()

    def world_to_screen(self, xs, ys, plot: PlotData):
        sx = (xs - plot.cposx) * plot.czoom * plot.unit + plot.viewx / 2
        sy = -(ys - plot.cposy) * plot.czoom * plot.unit + plot.viewy / 2
        return sx, sy

    def plot(self, data: PlotData):
        self.plots = []
        self.area_plots = []
        if self.error:
            return
        if data.step == 0:
            return
        xs = numpy.arange(data.start, data.stop, data.step)
        for function in self.numpy_functions:
            with numpy.errstate(divide="ignore", invalid="ignore"):
                try:
                    ys = function(xs, *data.variables)
                    if numpy.isscalar(ys):
                        ys = numpy.full_like(xs, ys)
                except (TypeError, NameError):
                    self.error = True
                    self.error_reason = "Expression uses undefined variables!"
                    print(f"ERROR: {self.error_reason}")
                    self.plots = []
                    return
            rs, re = xs, ys
            if self.kind == "y":
                (
                    rs,
                    re,
                ) = ys, xs
            try:
                rs, re = self.world_to_screen(rs, re, data)
                points = numpy.column_stack((rs, re))
            except Exception as e:
                self.error = True
                self.error_reason = str(e)
                print(f"ERROR: {self.error_reason}")
                self.plots = []
                return
            self.plots.append(points)
            if self.show_area:
                clamped = numpy.copy(points)
                clamped = clamped[~numpy.isnan(clamped).any(axis=1)]
                clamped[:, 1] = numpy.clip(clamped[:, 1], 0, data.view.y)
                self.area_plots.append(clamped)
        if len(self.plots) > 1 and not self.show_area:
            new_plots = []
            for i, plot in enumerate(self.plots):
                inside_mask = (
                    (plot[:, 0] >= 0)
                    & (plot[:, 0] <= data.view.x)
                    & (plot[:, 1] >= 0)
                    & (plot[:, 1] <= data.view.y)
                )
                inside_points = plot[inside_mask]
                new_plots.append(inside_points)
            self.plots = new_plots

    def compute(self, data: "UserData"):
        self.error = False
        self.error_reason = None
        self.numpy_functions = []
        self.solutions = []
        self.parameter = None
        if self.raw_string == "":
            self.computing = False
            return
        raw_left = None
        raw_right = None
        raw_str = self.raw_string.replace("^", "**")
        x, y = sympy.symbols("x,y")
        solve_for = y
        parameter = x
        self.kind = "x"
        if "=" in raw_str:
            raw_left, raw_right = raw_str.split("=", 1)
            if raw_left.strip() == "x":
                solve_for = x
                parameter = y
                self.kind = "y"
            try:
                lefte = sympy.sympify(raw_left)
                righte = sympy.sympify(raw_right)
                solutions = sympy.solve(sympy.Equality(lefte, righte), solve_for)
            except Exception as e:
                self.error = True
                self.error_reason = str(e)
                print(f"ERROR: {self.error_reason}")
                data.need_to_plot = True
                self.computing = False
                return
        else:
            raw_right = raw_str.strip()
            if "y" in raw_right:
                solve_for = x
                parameter = y
                self.kind = "y"
            try:
                solutions = sympy.solve(
                    sympy.Equality(
                        sympy.sympify(solve_for.name), sympy.sympify(raw_right)
                    ),
                    solve_for,
                )
            except Exception as e:
                self.error = True
                self.error_reason = str(e)
                print(f"ERROR: {self.error_reason}")
                data.need_to_plot = True
                self.computing = False
                return

        self.parameter = parameter
        self.solutions = solutions
        if self.show_derivative:
            self.compute_derivative(data)

        for solution in solutions:
            try:
                func = sympy.lambdify(
                    [parameter, *data.vars_symbols], solution, "numpy"
                )
                self.numpy_functions.append(func)
            except Exception as e:
                self.error_reason = str(e)
                print(f"ERROR: {self.error_reason}")
                self.computing = False
                data.need_to_plot = True
                return
        if len(self.numpy_functions) <= 0:
            self.error = True
            data.need_to_plot = True
            self.computing = False
            return
        data.need_to_plot = True
        self.computing = False

    def compute_derivative(self, data):
        if self.should_skip or not self.show_derivative:
            return
        self.derivatives = []
        self.derivative_funcs = []
        self.derivative_error = False
        self.derivative_error_reason = None
        error_count = 0
        error_reason = None
        for solution in self.solutions:
            try:
                if isinstance(solution, sympy.Abs):
                    inside = solution.args[0]
                    inside_left = -inside
                    inside_der_right = sympy.diff(inside, self.parameter)
                    inside_der_left = sympy.diff(inside_left, self.parameter)
                    inside_func_right = sympy.lambdify(
                        [self.parameter, *data.vars_symbols], inside_der_right, "numpy"
                    )
                    inside_func_left = sympy.lambdify(
                        [self.parameter, *data.vars_symbols], inside_der_left, "numpy"
                    )
                    inside_func = sympy.lambdify(
                        [self.parameter, *data.vars_symbols], inside, "numpy"
                    )
                    der_data = {
                        "left": inside_der_left,
                        "right": inside_der_right,
                        "inside": inside,
                    }
                    func_data = {
                        "left": inside_func_left,
                        "right": inside_func_right,
                        "inside": inside_func,
                    }
                    self.derivatives.append(der_data)
                    self.derivative_funcs.append(func_data)
                elif isinstance(solution, sympy.sign):
                    derivative = sympy.Number(0)
                    derivative_func = sympy.lambdify(
                        [self.parameter, *data.vars_symbols], derivative, "numpy"
                    )
                    self.derivatives.append(derivative)
                    self.derivative_funcs.append(derivative_func)
                else:
                    er = False
                    if "abs" in self.raw_string:
                        error_count += 1
                        error_reason = "Can only compute the derivative of abs if it's the main function"
                        er = True
                    for name in ["floor", "ceil", "sign", "sgn"]:
                        if name in self.raw_string:
                            error_count += 1
                            er = True
                            error_reason = f"Cannot compute the derivative containing the '{name}' function"
                    if not er:
                        derivative = sympy.diff(solution, self.parameter)
                        derivative_func = sympy.lambdify(
                            [self.parameter, *data.vars_symbols], derivative, "numpy"
                        )
                        self.derivatives.append(derivative)
                        self.derivative_funcs.append(derivative_func)
            except Exception as e:
                error_count += 1
                error_reason = str(e)
        if error_count == len(self.solutions):
            self.derivative_error = True
            self.derivative_error_reason = error_reason


class UserData:
    def __init__(self):
        self.expressions: list[UserExpression] = []
        self.variables: list[UserVariable] = []
        self.vars_symbols = []
        self.vars_values = []
        self.precision = 10000
        self.view = pygame.Vector2()
        self.cpos = pygame.Vector2()
        self.czoom = 1
        self.unit = 100
        self.need_to_plot = True
        self.panel_percentage = 0.2
        self.framerate = 120
        self.font_pad = 0
        self.font: pygame.Font = None
        self.font_size = FONT_SIZE
        self.font = pygame.font.SysFont("Segoe UI", FONT_SIZE)
        if os.path.exists("appdata/data.json"):
            self.load()

    def load(self):
        with open("appdata/data.json") as file:
            data = json.load(file)
            self.precision = data["precision"]
            self.panel_percentage = data["panel_percentage"]
            self.view = pygame.Vector2(data["view"])
            self.framerate = data["framerate"]
            for var in data["variables"]:
                self.variables.append(
                    UserVariable(var["name"], var["value"], var["vrange"])
                )
            self.refresh_vars_symbols()
            for expr in data["expressions"]:
                expr = UserExpression(expr["expr"], expr["color"])
                self.expressions.append(expr)
                expr.send_compute(self)
            self.need_to_plot = True

    def save(self):
        with open("appdata/data.json", "w") as file:
            json.dump(
                {
                    "panel_percentage": self.panel_percentage,
                    "precision": self.precision,
                    "view": (*self.view,),
                    "framerate": self.framerate,
                    "variables": [
                        {"name": var.name, "value": var.value, "vrange": var.vrange}
                        for var in self.variables
                    ],
                    "expressions": [
                        {"expr": expr.raw_string, "color": expr.color}
                        for expr in self.expressions
                    ],
                },
                file,
            )

    def refresh_vars_symbols(self):
        self.vars_symbols = [
            sympy.Symbol(var.name, real=True) for var in self.variables
        ]
        self.vars_values = [var.value for var in self.variables]

    def camera_to_range(self):
        view_world_width = self.view.x / (self.czoom * self.unit)
        view_world_height = self.view.y / (self.czoom * self.unit)

        x_start = self.cpos.x - view_world_width / 2
        x_end = self.cpos.x + view_world_width / 2

        y_start = self.cpos.y + view_world_height / 2
        y_end = self.cpos.y - view_world_height / 2

        x_step = (x_end - x_start) / self.precision
        y_step = (y_end - y_start) / self.precision

        return ((x_start, x_end, x_step), (y_start, y_end, y_step))

    def plot(self):
        (xs, xe, xst), (ys, ye, yst) = self.camera_to_range()
        plotx = PlotData(
            xs, xe, xst, self.vars_values, self.cpos, self.czoom, self.unit, self.view
        )
        ploty = PlotData(
            ys, ye, yst, self.vars_values, self.cpos, self.czoom, self.unit, self.view
        )
        for expression in self.expressions:
            plot = plotx
            if expression.kind == "y":
                plot = ploty
            expression.plot(plot)
        return [(xs, xe), (ys, ye)]

    def screen_to_world(self, screen_pos):
        return pygame.Vector2(
            (screen_pos[0] - self.view.x / 2) / self.czoom / self.unit + self.cpos.x,
            -(screen_pos[1] - self.view.y / 2) / self.czoom / self.unit + self.cpos.y,
        )

    def world_to_screen(self, world_pos):
        return pygame.Vector2(
            (world_pos[0] - self.cpos.x) * self.czoom * self.unit + self.view.x / 2,
            -(world_pos[1] - self.cpos.y) * self.czoom * self.unit + self.view.y / 2,
        )

    def draw_grid(self, screen: pygame.Surface, crange):
        (xs, xe), (ys, ye) = crange
        xw = abs(xe - xs)
        raw_step = xw / CELL_NUMBER
        cell_base = 10 ** numpy.floor(numpy.log10(raw_step))
        cell_candidates = numpy.array([1, 2, 5, 10]) * cell_base
        world_cell = cell_candidates[cell_candidates >= raw_step][0]
        cell_w = world_cell * self.unit * self.czoom
        world_left = numpy.floor(xs / world_cell) * world_cell
        world_top = numpy.floor(ys / world_cell) * world_cell
        cur_x = self.world_to_screen((world_left, 0)).x
        cur_y = self.world_to_screen((0, world_top)).y
        startx, starty = cur_x, cur_y
        for _ in range(CELL_NUMBER + 1):
            pygame.draw.line(screen, GRID_COL, (cur_x, 0), (cur_x, self.view.y))
            pygame.draw.line(screen, GRID_COL, (0, cur_y), (self.view.x, cur_y))
            cur_x += cell_w
            cur_y += cell_w
        center_scr = self.world_to_screen((0, 0))
        if xs < 0 < xe or xs < 0 < xe:
            pygame.draw.line(
                screen, AXIS_COL, (center_scr.x, 0), (center_scr.x, self.view.y)
            )
        if ys < 0 < ye or ye < 0 < ys:
            pygame.draw.line(
                screen, AXIS_COL, (0, center_scr.y), (self.view.x, center_scr.y)
            )
        return center_scr, startx, starty, cell_w, world_left, world_top, world_cell

    def draw_text(
        self,
        screen: pygame.Surface,
        center: pygame.Vector2,
        sx,
        sy,
        cell_w,
        wl,
        wt,
        world_cell,
    ):
        cur_x = sx
        cur_y = sy
        world_x = wl
        world_y = wt
        for _ in range(CELL_NUMBER + 1):
            rendery = True
            if abs(cur_x - center.x) <= 1:
                world_x = 0
            if abs(cur_y - center.y) <= 1:
                world_y = 0
                if 0 < center.x < self.view.x:
                    rendery = False
            x_surf = self.font.render(self.format_number(world_x), True, AXIS_COL)
            if rendery:
                y_surf = self.font.render(self.format_number(world_y), True, AXIS_COL)
            screen.blit(
                x_surf,
                x_surf.get_rect(
                    topleft=(
                        cur_x + self.font_pad,
                        pygame.math.clamp(
                            center.y + self.font_pad,
                            self.font_pad,
                            self.view.y - self.font_pad - x_surf.height,
                        ),
                    )
                ),
            )
            if rendery:
                screen.blit(
                    y_surf,
                    y_surf.get_rect(
                        topleft=(
                            pygame.math.clamp(
                                center.x + self.font_pad,
                                self.font_pad,
                                self.view.x - self.font_pad - y_surf.width,
                            ),
                            cur_y + self.font_pad,
                        )
                    ),
                )
            cur_x += cell_w
            cur_y += cell_w
            world_x += world_cell
            world_y -= world_cell

    def format_number(self, value, decimal_places=3, sci_threshold=5):
        if value == 0:
            return "0"
        abs_value = abs(value)
        if abs_value < 10**-sci_threshold or abs_value >= 10**sci_threshold:
            return f"{value:.{decimal_places}e}"
        else:
            return f"{value:.{decimal_places}f}".rstrip("0").rstrip(".")

    def draw_expressions(self, screen: pygame.Surface):
        for expression in self.expressions:
            if expression.should_skip:
                continue
            if expression.show_area:
                for plot in expression.area_plots:
                    try:
                        self.draw_area(expression, plot, screen)
                    except Exception as e:
                        print(f"ERROR: {e}")
            else:
                for i, plot in enumerate(expression.plots):
                    try:
                        pygame.draw.aalines(screen, expression.color, False, plot)
                    except Exception as e:
                        print(f"ERROR: {e}")

    def draw_area(self, expr: UserExpression, points, screen):
        zeroh = self.world_to_screen((0, 0)).y
        left = numpy.asarray([points[0][0], zeroh])
        right = numpy.asarray([points[-1][0], zeroh])
        pygame.draw.polygon(
            screen,
            expr.color,
            numpy.concatenate(
                [
                    numpy.asarray([left]),
                    points,
                    numpy.asarray([right]),
                ]
            ),
        )

    def get_closest_point(self, points, mouse):
        try:
            points = points[~numpy.isnan(points).any(axis=1)]
            if len(points) <= 0:
                return
            deltas = points - mouse
            dist_sq = numpy.sum(deltas**2, axis=1)
            idx = numpy.argmin(dist_sq)
            return points[idx]
        except Exception as e:
            print(f"ERROR: {e}")
            return

    def get_tangent_points(
        self, expr: UserExpression, derivative_func, numpy_function, mouse_coord
    ):
        with numpy.errstate(divide="ignore", invalid="ignore"):
            tangent_slope = derivative_func(mouse_coord, *self.vars_values)
        if numpy.isnan(tangent_slope) or numpy.isinf(tangent_slope):
            return
        with numpy.errstate(divide="ignore", invalid="ignore"):
            y0 = numpy_function(mouse_coord, *self.vars_values)
        if numpy.isnan(y0) or numpy.isinf(y0):
            return
        (xs, xe, xst), (ys, ye, _) = self.camera_to_range()
        tp = (mouse_coord, y0)
        if expr.kind == "x":
            xarr = numpy.asarray([xs, xe])
        else:
            xarr = numpy.asarray([ys, ye])
        yarr = tangent_slope * (xarr - mouse_coord) + y0
        rs, re = xarr, yarr
        if expr.kind == "y":
            (
                rs,
                re,
            ) = yarr, xarr
            tp = (y0, mouse_coord)
        rs, re = expr.world_to_screen(
            rs,
            re,
            PlotData(
                xs,
                xe,
                xst,
                self.variables,
                self.cpos,
                self.czoom,
                self.unit,
                self.view,
            ),
        )
        return (
            numpy.column_stack((rs, re)),
            self.world_to_screen(tp),
            tangent_slope,
            tp[1],
        )

    def update(self, screen: pygame.Surface):
        if self.need_to_plot:
            self.view = pygame.Vector2(screen.size)
            crange = self.plot()
            screen.fill("black")
            center, sx, sy, cw, wl, wt, wc = self.draw_grid(screen, crange)
            self.draw_expressions(screen)
            self.draw_text(screen, center, sx, sy, cw, wl, wt, wc)
            self.need_to_plot = False

    def reset_cam(self):
        self.cpos = pygame.Vector2(0, 0)
        self.czoom = 1
        self.need_to_plot = True
