#from symengine import symbols #lambdify #sympify, solve
import numpy as np
from sympy import sympify, solve, Equality, lambdify, symbols
import time

# Step 1: Parse the expression from a string
expr_str = "y + x = x**2 - sin(ln(x))"
left, right = expr_str.split("=")
x, y = symbols('x y')
lefte = sympify(left)  # Parses to an equality
righte = sympify(right)

# Step 2: Solve the equation symbolically for y
solved = solve(Equality(lefte, righte), y)[0]  # We expect one solution: y = something
# solved is now: x**2 - sin(log(x)) - x

# Step 3: Convert to a NumPy-friendly function
func = lambdify(x, solved,'numpy')

# Step 4: Define your x range and evaluate the function
def evaluate_range(start, stop, step):
    xs = np.arange(start, stop, step)
    with np.errstate(divide='ignore', invalid='ignore'):
        ys = func(xs)  # This is vectorized; no Python loop
    return xs, ys

# Example: range from 1 to 10 with step 0.01
start = time.perf_counter()
sta, sto, ste = -1, 10, 0.00001
xs, ys = evaluate_range(sta, sto, ste)
print((sto-abs(sta))/ste)
print(time.perf_counter()-start)
print(ys[0])

# Optional: Print a sample
#print(f"x[0:5]: {xs[:5]}")
#print(f"y[0:5]: {ys[:5]}")