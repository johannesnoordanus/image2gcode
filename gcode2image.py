
"""
gcode2image: convert gode to image.
"""

import sys
import argparse
from datetime import datetime
from PIL import Image
import numpy as np
# typical gcode:
#G0 X10.0 Y10.0
#G1 F2000
#X56.4 S0
#Y10.1 S0
#X25.1 S0
#X24.9 S2
#X24.8 S4
#X24.7 S7
#X24.6 S9
#X24.5 S20
#X24.4 S55
#X24.3 S78
#X24.2 S42
#X24.1 S28
#X24.0 S58
#X23.9 S62
#X10.0 S0
#Y10.2 S0
#X23.7 S0

def gcode2image(gcode: str = None, width: int = None, height: int = None, dimensions: (int,int) = None):

    # array (hight,width) with unsigned 8 bit elements
    image = np.empty([height, width], dtype=np.uint8)
    str_index = 0

    # offset (X,Y)
    start_X = None
    start_Y = None
    # current (x,y)
    x = None
    y = None

    def set_coordinates(X = None,Y = None,S = None):
            if X:
                for x in X:
                    array[x-start_X,y-start_Y] = S
            if Y:
                y = Y-start_Y
            if ( x == X ):
                raise ValueError("Linear move should not go to the same location on a line: ({x},{y}) -> ({X},{y})")
            if x < X:
                for x_coord in range(x,X):
                    image[y,x_coord] = S
            else:
                for x_coord in range(X,x,-1):
                    image[y,x_coord] = S
            x = X

            print(number)

    def G0(index: int) -> int:
         # find next G0
         # get X and Y (until /n)

        # set inital values
        start_X = X
        start_Y = Y
        x = start_X
        y = start_Y

        return index

    def G1(index: int) -> (int, int):
        # find next G1
        # get X (and S) or get Y (until /n)
        if X:
           # get X coordinate,
           # get S,
           set_coordinates(X,S)
        if Y:
           set_coordinates(Y)

        return index

     # find G0 (set start_X/Y and x,y)

     #repead until end of string
     #    find G1 and set array coordinates and (inverse) intensity
