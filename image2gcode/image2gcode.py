"""
image2gcode: convert an image to gcode.
"""

import os
import sys
import math
import argparse
from argparse import Namespace
from datetime import datetime
from collections import namedtuple
from collections.abc import Callable
from typing import Any
from typing import Tuple

from PIL import Image
import numpy as np

from image2gcode.boundingbox import Boundingbox

# pip install nptyping[complete]
# https://github.com/ramonhagenaars/nptyping/blob/master/USERDOCS.md#Quickstart
from nptyping import NDArray, UInt8, Shape

class Image2gcode:
    """
    Class Image2gcode handles the conversion of an image to gcode.
    """

    def __init__(self, power: Callable[[UInt8,int,int,bool],int] = None,
                 transformation: Callable[[Tuple[float,float]],Tuple[float,float]] = None):

        # init
        self.bbox = Boundingbox()
        self._power = power if power is not None else self.linear_power
        self._transformation = transformation

    def distance(self, A: Tuple[float,float], B: Tuple[float,float]) -> float:
        """
        Pythagoras
        """
        # |Ax - Bx|^2 + |Ay - By|^2 = C^2
        # distance = √C^2
        return math.sqrt(abs(A[0] - B[0])**2 + abs(A[1] - B[1])**2)

    @staticmethod
    def linear_power(pixel: UInt8, maxpower: int, offset: int = 0, invert: bool = True) -> int:
        """
        Linear conversion of pixel value to laser intensity

        :param pixel: int range [0-255]
        :param maxpower: machine maximum laser power (typically [0-1000])
        :param offset: int range [0-maxpower] (shift power range)
        :param invert: true/false (default true, when true 'black == white')
        :return: laser intensity for this pixel
        """
        return offset + round((1.0 - float(pixel/255)) * (maxpower - offset)) if invert else round(float(pixel/255) * (maxpower - offset))


    def image2gcode(self, img: NDArray[Shape["*,*"], UInt8], args: dict[str, Any]) -> str:
        """
        :param img: image array (widthx,height), intensity values [0-255]
        :param args: conversion settings (like pixelsize, speed, maxpower, ..)
        :return: gcode for this img(age)

        algorithm outline:
            scan image left to right, shift one scan line down, then right to left
                for each scan line,
                    for each pixel on the scan line,
                        convert pixel intensity to laser power,
                        generate gcode for the current coordinates (X,Y) at this intensity
                repeat

        Note that the algorithm outline does not cover the subtleties.
        In general, the laser machine head moves only when needed and does not always
        follow the image scan order, empty (0 burn or noise pixels) are skipped which
        alltogether generates the effect that only image objects within their contour
        are 'printed'

        detail:
         emit condensed gcode:
          - emit XY coordinates only when they change
          - emit modal gcode (linear move G1/G0) minimally
          - does not emit zero power (or below cutoff/noise) pixels

         optimizations:
          - draw pixels only when change of power
          - minimal laser head moves: laser head has defered and sparse moves.
            (XY locations are virtual, head does not always follow)
          - moves at high speed (G0) over 10mm (default) or more zero pixels
          - low burn levels (noise pixels) can be suppressed (default off)
          - overscan image: set laserhead a few pixels before the first pixels of a scan line,
            and move head a few pixels after the last pixels of a scan line (both directions)
            default off
            (this might reduce low burnrate pixels at the edges for some laser machines,
            note that speed adaptive burn mode M4 should automatically take care of this.)
        """

        def XYdelta(XY: Tuple[float,float]) -> Tuple[float,float]:
            """
            This function does a transformation.
            :param XY: point to transform
            :return: transformation of XY
            """
            XYd = XY if self._transformation is None else self._transformation(XY)
            return (round(XYd[0],XY_prec),round(XYd[1],XY_prec))

        def handle_overscan_at_eol(lastnoise):
            """
            This functions is called at the end of a scan line.
            It moves the laser head just after the last contour (point) of this line.
            :param lastnoise: location of the last 'noise' point
            :return: gcode to move the head to this location
            """
            nonlocal gcode
            nonlocal head

            # we are at the end of a scan line
            if args["overscan"] and head[1] == Y and lastnoise is not None:
                # we are past the (outer) contour of this image (that is: one or more points are drawn on
                # this line and one or more zero power pixels are not drawn)
                # we now add a few pixels to be drawn past this edge (nomally zero/noise pixels are skipped),
                # to make the laser head moves a few pixels further in the same scan direction
                if left2right:
                    overscanpixels = min(round(head[0] + (args["overscan"] * args["pixelsize"]), XY_prec),
                                         round(args["offset"][0] + (line.size * args["pixelsize"]), XY_prec))
                else:
                    overscanpixels = max(round(head[0] - (args["overscan"] * args["pixelsize"]), XY_prec),
                                         round(args["offset"][0], XY_prec))

                # get points after transformation (if any)
                overscandelta, Yd = XYdelta((overscanpixels,Y))
                # emit overscan pixels
                overscan = "180" if (args["overscan"] and args["showoverscan"]) else "0"
                gcode += [f"X{overscandelta}Y{Yd}S{overscan}"]

                # head at this location
                head = (overscanpixels,Y)

        def handle_overscan_at_begin_of_line(lastnoise) -> str:
            """
            This functions is called at the beginning of a scan line.
            It moves the laser head just before the first contour (point) of this line.
            :param lastnoise: location of the last 'noise' point
            :return: gcode to move the head to this location
            """
            code = ''
            # we are at the beginning of a scan line
            if args["overscan"] and head[1] != Y:
                # the laser head is still at aprevious line and is moved to this line, just a few
                # pixels before the start of a contour of this image
                if left2right:
                    # go to next line and start overscan pixels earlier
                    min_X = round(args["offset"][0], XY_prec)
                    overscanpixels = round(lastnoise[0] - (args["overscan"] * args["pixelsize"]), XY_prec)
                    overscanpixels = overscanpixels if overscanpixels > min_X else min_X
                else:
                    max_X = round(args["offset"][0] + (line.size * args["pixelsize"]), XY_prec)
                    overscanpixels = round(lastnoise[0] + (args["overscan"] * args["pixelsize"]), XY_prec)
                    overscanpixels = overscanpixels if overscanpixels < max_X else max_X

                # get points after transformation (if any)
                overscandelta, lastnoisedelta = XYdelta((overscanpixels,lastnoise[1]))

                # go to overscan position
                code = f"X{overscandelta}Y{lastnoisedelta}S0\n"
            return code

        def handle_lastnoise(lastnoise) -> str:
            """
            This functions is called to move the laser head to the correct location
            before a point is emmitted.
            :param lastnoise: location of the last 'noise' point
            :return: gcode to move the head to this location
            """
            code = ""
            if lastnoise:
                # head is not at correct location, go there

                # Apply affine transformation (if needed)
                # (Note that an affine transformation does not necessarily preserve angles between
                # lines or distances between points!)
                XYlastnoise = XYdelta(lastnoise)
                XYhead = XYdelta(head)

                # move head to location just before a new point is emitted
                # (note that 'noise' points are not emitted and the laser head has to
                # catch up with the last noise point location, to be able to write a new pixel)
                if args["speedmoves"] and (self.distance(XYhead,XYlastnoise) > args["speedmoves"]):
                    # fast
                    code = f"G0 X{XYlastnoise[0]}Y{XYlastnoise[1]}\nG1\n"
                else:
                    # normal speed
                    code = handle_overscan_at_begin_of_line(lastnoise)
                    overscan = "180" if (args["overscan"] and args["showoverscan"]) else "0"
                    code += f"X{XYlastnoise[0]}Y{XYlastnoise[1]}S{overscan}\n"

                # update bounding box
                self.bbox.update(XYlastnoise)
            return code

        # set X/Y-axis precision to number of digits after
        XY_prec = len(str(args["pixelsize"]).split('.')[1])

        # set printer start coordinates
        X = round(args["offset"][0], XY_prec)
        Y = round(args["offset"][1], XY_prec)

        # get coordinates after transformation (if any)
        Xd, Yd = XYdelta((X,Y))

        # go to start
        gcode = [f"G0X{Xd}Y{Yd}"]
        # current location of laser head
        head = (X,Y)

        # initiate bbox
        self.bbox.update((Xd,Yd))

        # set write speed and G1 move mode
        # (note that this stays into effect until another G code is executed,
        #  so we do not have to repeat this for all coordinates emitted below)
        gcode += [f"G1F{args['speed']}"]

        left2right = True

        # start image conversion
        for line in img:

            if not left2right:
                # reverse line when printing right to left
                line = np.flip(line)

            # add line terminator (makes this algorithm regular)
            line = np.append(line,0)

            # Note that (laser) drawing from a point to a point differs from setting a point (within an image):
            #              0   1   2   3   4   5   6     <-- gcode drawing points
            # one line:    |[0]|[1]|[2]|[3]|[4]|[5]|     <-- image pixels
            #
            # For example: drawing from X0 to X2 with value S10 corresponds to setting [0] = S10 and [1] = S10
            # Note also that drawing form left to right differs subtly from the reverse

            # draw this pixel line
            for count, pixel in enumerate(line):
                laserpow = self._power(pixel, args["maxpower"], args["poweroffset"], args["invert"])

                if count == 0:
                    # delay emit first pixel (so all same power pixels can be emitted in one sweep)
                    prev_pow = laserpow
                    # set last noise location on start of the line
                    lastnoise = (X,Y)

                # draw pixels when change of power
                if laserpow != prev_pow or count == line.size-1:
                    # skip all zero power points
                    if prev_pow > args["noise"]:

                        # check if head is at the right location, if not go there
                        code = handle_lastnoise(lastnoise)

                        # emit point
                        if self._transformation is not None:
                            Xd, Yd = XYdelta((X,Y))
                            code += f"X{Xd}Y{Yd}S{prev_pow}"
                            # update bbox
                            self.bbox.update((Xd,Yd))
                        else:
                            code += f"X{X}S{prev_pow}"
                            # update bbox
                            self.bbox.update((X,Y))
                        gcode += [code]

                        # head at this location
                        head = (X,Y)
                        lastnoise = None
                    else:
                        # didn't move head to location, save it
                        lastnoise = (X,Y)

                    if count == line.size-1:
                        # overscan this line (if we can)
                        handle_overscan_at_eol(lastnoise)
                        continue
                    prev_pow = laserpow # if laserpow != prev_pow

                # next point
                X = round(X + (args["pixelsize"] if left2right else -args["pixelsize"]), XY_prec)

            # next scan line (defer head movement)
            Y = round(Y + args["pixelsize"], XY_prec)

            # change print direction
            left2right = not left2right

        return '\n'.join(gcode)
