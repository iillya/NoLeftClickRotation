"""Contains a basic math library used by some of the modeling examples.

This file does not contain any ZBrush specific functionality. THIS IS STILL A CODE EXAMPLE AND NOT 
A FEATURE. We cannot debug or extend this library. But it can be starting point for you to fill some
gaps in ZBrush's current API.

Functions:

    interpolate:    Linearly interpolates between two values.

Classes:

    Vector:         Represents a three-dimensional floating point vector.
    ValueNoise:     Realizes a naive value noise.

"""
__author__ = "Ferdinand Hoppe"
__date__ = "22/08/2025"
__copyright__ = "Maxon Computer"

import math
import typing

def interpolate(a: float, b: float, t: float) -> float:
    """Linearly interpolates between #a and #b using #t.
    """
    return a + t * (b - a)

class Vector:
    """Represents a three-dimensional floating point vector.

    Implements basic vector operations and supports iteration over its components to allow unpacking.
    I.e., you can do the following:

        v: Vector = Vector(1.0, 2.0, 3.0)

        def foo(x: float, y: float, z: float) -> None:
            ...

        foo(*v)
    """
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        """Constructs a vector.
        """
        self.x = x; self.y = y; self.z = z

    def __add__(self, other: "Vector") -> "Vector":
        """Adds #other to #self and returns the result.
        """
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __iadd__(self, other: "Vector") -> "Vector":
        """Adds #other to #self.
        """
        self.x += other.x; self.y += other.y; self.z += other.z
        return self

    def __sub__(self, other: "Vector") -> "Vector":
        """Subtracts #other from #self and returns the result.
        """
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __isub__(self, other: "Vector") -> "Vector":
        """Subtracts #other from #self.
        """
        self.x -= other.x; self.y -= other.y; self.z -= other.z
        return self

    def __mul__(self, other: float) -> "Vector":
        """Multiplies #self by the scalar #other and returns the result.
        """
        return Vector(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other: float) -> "Vector":
        """Multiplies a scalar by #self and returns the result.
        """
        return self * other

    def __imul__(self, other: float) -> "Vector":
        """Multiplies #self by the scalar #other.
        """
        self.x *= other; self.y *= other; self.z *= other
        return self

    def __iter__(self) -> typing.Iterator[float]:
        """Iterates over the components of the vector.
        """
        yield self.x
        yield self.y
        yield self.z

    def __repr__(self) -> str:
        """Returns a string representation of the vector.
        """
        return (f"{self.__class__.__name__}({round(self.x, 3)}, {round(self.y, 3)}, "
                f"{round(self.z, 3)})")

    def dot(self, other: "Vector") -> float:
        """Returns the dot product of #self and #other.
        """
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other: "Vector") -> "Vector":
        """Returns the cross product of #self and #other.
        """
        return Vector(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length(self) -> float:
        """Returns the length of #self.
        """
        return math.sqrt(self.length_squared())

    def length_squared(self) -> float:
        """Returns the squared length of #self.
        """
        return self.x ** 2 + self.y ** 2 + self.z ** 2

    def normalized(self) -> "Vector":
        """Returns the unit vector of #self.
        """
        length = self.length()
        if length > 0:
            return Vector(self.x / length, self.y / length, self.z / length)
        return Vector()

    def rotate(self, angles: "Vector") -> "Vector":
        """Rotates #self by the given Euler #angles in radians.
        """
        x, y, z = self.x, self.y, self.z
        cx, cy, cz = map(math.cos, (angles.x, angles.y, angles.z))
        sx, sy, sz = map(math.sin, (angles.x, angles.y, angles.z))
        return Vector(
            x * cy * cz - y * cy * sz + z * sy,
            x * (sx * sy * cz + cx * sz) + y * (cx * sy * sz - sx * cz) - z * sx * cy,
            x * (-cx * sy * cz + sx * sz) + y * (sx * sy * sz + cx * cz) + z * cx * cy
        )

class ValueNoise:
    """Realizes a naive value noise generator.

    This was written for the lightning curves example and is not by any means a production quality
    noise implementation. It is just meant to demonstrate how you could implement a simple value
    noise in Python using the Vector class defined above.
    """
    SEED: float = 43758.5453 # The seed used by the hash function.

    @staticmethod
    def hash_31(p: Vector) -> float:
        """Returns a pseudo random hash value for the given vector #p.
        """
        return ((math.sin(p.x * 12.9898 + p.y * 78.233 + p.z * 37.719) * ValueNoise.SEED) % 1.0)

    @staticmethod
    def noise_31(p: Vector, scale: float = 1.0) -> float:
        """Returns a noise float value for the given vector #p.
        """
        # Get the integer cell coordinate and the local coordinate within the cell for the vector #p.
        cell: Vector = Vector(math.floor(p.x), math.floor(p.y), math.floor(p.z))
        local: Vector = Vector(p.x - cell.x, p.y - cell.y, p.z - cell.z)

        # Compute the pseudo random hashes for the eight corners of the cell.
        v000: float = ValueNoise.hash_31(Vector(cell.x, cell.y, cell.z))
        v001: float = ValueNoise.hash_31(Vector(cell.x, cell.y, cell.z+1))
        v010: float = ValueNoise.hash_31(Vector(cell.x, cell.y+1, cell.z))
        v011: float = ValueNoise.hash_31(Vector(cell.x, cell.y+1, cell.z+1))
        v100: float = ValueNoise.hash_31(Vector(cell.x+1, cell.y, cell.z))
        v101: float = ValueNoise.hash_31(Vector(cell.x+1, cell.y, cell.z+1))
        v110: float = ValueNoise.hash_31(Vector(cell.x+1, cell.y+1, cell.z))
        v111: float = ValueNoise.hash_31(Vector(cell.x+1, cell.y+1, cell.z+1))

        # Compute the result by bilinearly interpolating the the cell corners. Here is a lot of
        # room for optimization, e.g., by using a smoother interpolation function, as linear
        # interpolation produces visible artifacts.
        x00: float = interpolate(v000, v100, local.x)
        x01: float = interpolate(v001, v101, local.x)
        x10: float = interpolate(v010, v110, local.x)
        x11: float = interpolate(v011, v111, local.x)
        y0: float = interpolate(x00, x10, local.y)
        y1: float = interpolate(x01, x11, local.y)
        return interpolate(y0, y1, local.z) * scale

    @staticmethod
    def noise_13(p: float, scale: float = 1.0) -> Vector:
        """Returns a noise vector for the given float value #p.
        """
        return Vector(
            ValueNoise.noise_31(Vector(p, 0, 0), scale),
            ValueNoise.noise_31(Vector(0, p, 0), scale),
            ValueNoise.noise_31(Vector(0, 0, p), scale)
        )
    
    @staticmethod
    def turbulence_13(p: float, scale: float = 1.0, octaves: int = 4, frequency: float = 1.0, 
                      amplitude: float = 1.0) -> Vector:
        """Returns a turbulence vector for the given float value #p.
        """
        res: Vector = Vector()
        for _ in range(octaves):
            res += ValueNoise.noise_13(p * frequency, scale) * amplitude
            frequency *= 2.0
            amplitude *= 0.5
        return res