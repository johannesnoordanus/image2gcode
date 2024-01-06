"""
Boundingbox in 2 dimensions.
"""
import copy
from collections import namedtuple

# declare tuple types
Point = namedtuple('Point', ['x', 'y'])
Bbox = namedtuple('Bbox', ['lowerleft', 'upperright'])

class Boundingbox:
    """
    Boundingbox in 2 dimensions.
    """

    def __init__(self, point: Point = None):
        self._bbox = None
        if point:
            self.update(Point(*point))

    def __repr__(self):
        return (f"Boundingbox: (X{round(self._bbox.lowerleft.x,2)},Y{round(self._bbox.lowerleft.y,2)}:"
                f"X{round(self._bbox.upperright.x,2)},Y{round(self._bbox.upperright.y,2)})")

    def update(self, point: Point):
        """
        update bounding box

        :param point: (X,Y)
        """
        # cast from unnamed tuple (float,float)
        point = Point(*point)
        if self._bbox is not None:
            self._bbox = Bbox( Point( point.x if point.x < self._bbox.lowerleft.x else self._bbox.lowerleft.x,
                                      point.y if point.y < self._bbox.lowerleft.y else self._bbox.lowerleft.y ),
                               Point( point.x if point.x > self._bbox.upperright.x else self._bbox.upperright.x,
                                      point.y if point.y > self._bbox.upperright.y else self._bbox.upperright.y ) )
        else:
            self._bbox = Bbox(lowerleft = copy.deepcopy(point), upperright = copy.deepcopy(point))

    def get(self) -> Bbox:
        """
        get bounding box
        """
        return self._bbox

    def center(self) -> Point:
        """
        get center of bounding box
        """
        return Point( x = abs(self._bbox.upperright.x - self._bbox.lowerleft.x)/2.0 + self._bbox.lowerleft.x,
                      y = abs(self._bbox.upperright.y - self._bbox.lowerleft.y)/2.0 + self._bbox.lowerleft.y )

    def check(self, point: Point) -> bool:
        """
        check if coordinates within bounding box bounds

        :param point: (X,Y)
        :return true if within bounds, otherwise false
        """
        # cast from unnamed tuple (float,float)
        point = Point(*point)
        return ( point.x >= self._bbox.lowerleft.x and point.y >= self._bbox.lowerleft.y
                 and point.x <= self._bbox.upperright.x and point.y <= self._bbox.upperright.y )

    def size(self) -> float:
        """
        get bounding box size
        """
        return (self._bbox.upperright.x - self._bbox.lowerleft.x) * (self._bbox.upperright.y - self._bbox.lowerleft.y)

if __name__ == '__main__':
    p = Point(0,0)
    print(f"type: {type(p)}")
    print(f"{p}")
    bbox = Boundingbox()
    bbox = Boundingbox(p)
    bbox = Boundingbox((10,20))

    print(bbox.get())
    print(bbox.center())
    print(bbox.check(p))
    print(bbox.check((2,3)))
    print(bbox.check((10,20)))
    print(bbox.update((40,60)))
    print(bbox.get())
    print(bbox.update((30,30)))
    print(bbox.get())
    print(bbox.check((30,40)))

    b = bbox.get()
    print(f"b: {b}");
    print(f"b lowerleft: {b[0]}");
    print(f"b upperright: {b[1]}");
    print(f"b lowerleft x: {b[0][0]}");
    print(f"b upperright x: {b[1][0]}");
    print(f"b lowerleft y: {b[0][1]}");
    print(f"b upperright y: {b[1][1]}");
    print(bbox)
