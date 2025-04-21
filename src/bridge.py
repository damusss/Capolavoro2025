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
        self.entry = mili.EntryLine(
            self.raw_string, ENTRY_STYLE | {"placeholder": "Enter expression..."}
        )
        self.computing = False
        self.collapsed = True
        self.hidden = False
        self.show_derivative = False
        self.show_area = False
        self.area_plots = []
        self.derivative = None
        self.derivative_error = False
        self.derivative_error_reason = False
        self.numpy_functions = []
        self.solutions = []
        self.parameter = None

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
                # Clamp X (column 0)
                clamped = numpy.copy(points)
                clamped = clamped[~numpy.isnan(clamped).any(axis=1)]
                # Clamp Y (column 1)
                clamped[:, 1] = numpy.clip(clamped[:, 1], 0, data.view.y)
                self.area_plots.append(clamped)

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
        if self.should_skip or self.should_skip_derivative:
            return
        self.derivative_error = False
        self.derivative_error_reason = None
        if len(self.solutions) > 1:
            self.derivative_error = True
            self.derivative_error_reason = (
                "Not supported for expressions with multiple solutions"
            )
            return
        try:
            self.derivative = sympy.Derivative(
                self.solutions[0],
                self.parameter,
            ).doit()
            self.derivative_func = sympy.lambdify(
                [self.parameter, *data.vars_symbols], self.derivative, "numpy"
            )
        except Exception as e:
            self.derivative_error = True
            self.derivative_error_reason = str(e)


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

        y_start = self.cpos.y - view_world_height / 2
        y_end = self.cpos.y + view_world_height / 2

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

    def draw(self, screen: pygame.Surface):
        screen.fill(0)
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
                for plot in expression.plots:
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

    def get_tangent_points(self, expr: UserExpression, mouse_coord):
        with numpy.errstate(divide="ignore", invalid="ignore"):
            tangent_slope = expr.derivative_func(mouse_coord, *self.vars_values)
        if numpy.isnan(tangent_slope) or numpy.isinf(tangent_slope):
            return
        with numpy.errstate(divide="ignore", invalid="ignore"):
            y0 = expr.numpy_functions[0](mouse_coord, *self.vars_values)
        if numpy.isnan(y0) or numpy.isinf(y0):
            return
        (xs, xe, xst), (ys, ye, _) = self.camera_to_range()
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
        return numpy.column_stack((rs, re))

    def update(self, screen: pygame.Surface):
        if self.need_to_plot:
            self.view = pygame.Vector2(screen.size)
            self.plot()
            self.draw(screen)
            self.need_to_plot = False
