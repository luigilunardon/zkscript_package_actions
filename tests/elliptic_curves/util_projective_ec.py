from copy import deepcopy

from elliptic_curves.fields.prime_field import PrimeField
from elliptic_curves.models.ec import ShortWeierstrassEllipticCurve, ShortWeierstrassEllipticCurvePoint


def add(lhs: list[PrimeField], rhs: list[PrimeField], field: PrimeField) -> list[PrimeField]:
    """Compute `lhs + rhs` where `lhs`, `rhs` are points on an EC in projective coordinates."""
    if rhs == [field.zero(), field.identity(), field.zero()]:
        return lhs
    if lhs == [field.zero(), field.identity(), field.zero()]:
        return rhs
    if (lhs[0] * rhs[2] == rhs[0] * lhs[2]) and (lhs[1] * rhs[2] + lhs[2] * rhs[1] == field.zero()):
        return [field.zero(), field.identity(), field.zero()]
    # lhs = [x, y, z]
    u = lhs[2] * rhs[1] - lhs[1] * rhs[2]  # y2 * z1 - y1 * z2
    v = lhs[2] * rhs[0] - lhs[0] * rhs[2]  # x2 * z1 - x1 * z2
    a = u * u * lhs[2] * rhs[2] - v * v * v - field(2) * v * v * lhs[0] * rhs[2]

    return [v * a, u * (v * v * lhs[0] * rhs[2] - a) - v * v * v * lhs[1] * rhs[2], v * v * v * lhs[2] * rhs[2]]


def double(self: list[PrimeField], curve: ShortWeierstrassEllipticCurve, field: PrimeField) -> list[PrimeField]:
    """Compute `2*self` where `self` is a point on an EC in projective coordinates."""
    if self == [field.zero(), field.identity(), field.zero()]:
        return self

    s = self[1] * self[2]
    B = self[0] * self[1] * s
    w = curve.a * self[2].power(2) + self[0].power(2) * field(3)
    h = w.power(2) - B * field(8)

    return [h * s * field(2), w * (B * field(4) - h) - s.power(2) * self[1].power(2) * field(8), s.power(3) * field(8)]


def multiply(
    self: list[PrimeField], scalar: int, curve: ShortWeierstrassEllipticCurve, field: PrimeField
) -> list[PrimeField]:
    """Compute `scalar * self` where `self` is a point on an EC in projective coordinates."""
    if scalar == 0:
        return [field.zero(), field.identity(), field.zero()]

    exp_scalar = [int(bin(scalar)[j]) for j in range(2, len(bin(scalar)))]
    T = deepcopy(self)

    for e in exp_scalar[1:]:
        T = double(T, curve, field)
        if e == 1:
            T = add(self, T, field)

    return T


def negate(self: list[PrimeField]) -> list[PrimeField]:
    """Compute `-self` where `self` is a point on an EC in projective coordinates."""
    return [self[0], -self[1], self[2]]


def to_proj(point: ShortWeierstrassEllipticCurvePoint, field: PrimeField) -> list[PrimeField]:
    """Convert `point` from affine to projective coordinates."""
    return [point.x, point.y, field.identity()]


def to_aff(
    point: list[PrimeField], curve: ShortWeierstrassEllipticCurve, field: PrimeField
) -> ShortWeierstrassEllipticCurvePoint:
    """Convert `point` from projective to affine coordinates."""
    return (
        curve(
            point[0] * point[2].invert(),
            point[1] * point[2].invert(),
            False,
        )
        if not point[2].is_zero()
        else curve(field.identity(), field.identity(), True)
    )


def proj_to_list(point):
    """Return the list of coordinates of `point` as integers."""
    return [element.to_int() for element in point]


def multi_addition(points: list[list[PrimeField]], field: PrimeField, n_points_on_altstack: int) -> list[PrimeField]:
    """Compute multi addition for points in projective coordinates.

    We compute the following sum:
        result = ((points[n_points_on_stack-1] + points[n_points_on_stack-2]) + .. ) + points[0])
        result = points[-1] + (.. + points[n_points_on_stack+1] + (points[n_points_on_stack] + result)))
    """
    assert n_points_on_altstack <= len(points)

    n_points_on_stack = len(points) - n_points_on_altstack
    result = [field.zero(), field.identity(), field.zero()]
    for point in points[:n_points_on_stack][::-1]:
        result = add(result, point, field)
    for point in points[n_points_on_stack:][::-1]:
        result = add(point, result, field)

    return result


def msm(
    scalars: list[int], bases: list[list[PrimeField]], curve: ShortWeierstrassEllipticCurve, field: PrimeField
) -> list[PrimeField]:
    """Compute the multi scalar multiplication between `scalars` and `bases`."""
    multiplications = [multiply(base, scalar, curve, field) for (scalar, base) in zip(scalars, bases)]
    expected = multiplications[-1]
    for multiplication in multiplications[:-1][::-1]:
        expected = add(multiplication, expected, field)

    return expected


def generate_multi_addition_tests(points: list[list[PrimeField]], field: PrimeField):
    """Generate test data for multi addition."""
    n_points = len(points)
    out = []
    for i in range(n_points + 1):
        out.append(
            {
                "points": points,
                "expected": multi_addition(points, field, i),
                "n_points_on_altstack": i,
            }
        )

    return out


def double_fq2(point, curve, field, extension_field):
    """Compute `2*point` where `point` is a point on an EC in projective coordinates."""
    X = point[0]
    Y = point[1]
    Z = point[2]
    a = curve.a

    two = extension_field(field(2), field(0))
    three = extension_field(field(3), field(0))
    T = three * X * X + a * Z * Z
    U = two * Y * Z
    V = two * U * X * Y
    W = T * T - two * V

    X1 = U * W
    Y1 = T * (V - W) - two * (U * Y * U * Y)
    Z1 = U * U * U

    return [X1, Y1, Z1]


def add_fq2(point_1, point_2):
    """Compute `point_1 + point_2` where the points are in projective coordinates."""
    X1 = point_1[0]
    Y1 = point_1[1]
    Z1 = point_1[2]
    X2 = point_2[0]
    Y2 = point_2[1]
    Z2 = point_2[2]

    T = Y1 * Z2 - Y2 * Z1
    U = X1 * Z2 - X2 * Z1
    V = X1 * Z2 + X2 * Z1
    W = T * T * Z1 * Z2 - U * U * V

    X3 = U * W
    Y3 = T * (X1 * Z2 * U * U - W) - Z2 * Y1 * U * U * U
    Z3 = U * U * U * Z1 * Z2
    return [X3, Y3, Z3]


def negate_fq2(point):
    """Compute `-point` where `point` is a point on an EC in projective coordinates."""
    X = point[0]
    Y = point[1]
    Z = point[2]
    return [X, -Y, Z]


def proj_point_to_script_fq2(point):
    return [val for coord in [[i.x0.to_int(), i.x1.to_int()] for i in point] for val in coord]
