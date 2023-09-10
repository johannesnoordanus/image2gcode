#!/usr/bin/env python3
"""
image2gcode: convert an image to gcode.
"""
__version__ = "2.7.0"

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

# pip install nptyping[complete]
# https://github.com/ramonhagenaars/nptyping/blob/master/USERDOCS.md#Quickstart
from nptyping import NDArray, UInt8, Shape

GCODE2IMAGE = True
try:
    from gcode2image import gcode2image
except ImportError:
    GCODE2IMAGE = False

from boundingbox import Boundingbox

class Image2gcode:
    """
    Class Image2gcode handles the conversion of an image to gcode.
    """

    def __init__(self, power: Callable[[UInt8,int,bool],int] = None,
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

    def linear_power(self, pixel: UInt8, maxpower: int, offset: int = 0, invert: bool = True) -> int:
        """
        Linear conversion of pixel value to laser intensity

        :param pixel: int range [0-255]
        :param maxpower: machine maximum laser power (typically [0-1000])
        :param offset: int range [0-maxpower] (shift power range)
        :param invert: true/false (default true, when true 'black = white')
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
                                         round(args.offset[0], XY_prec))

                # get points after transformation (if any)
                overscandelta, Yd = XYdelta((overscanpixels,Y))
                # emit overscan pixels
                gcode += [f"X{overscandelta}Y{Yd}S0"]

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
                    code += f"X{XYlastnoise[0]}Y{XYlastnoise[1]}S0\n"

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
        self.bbox.update((X,Y))

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
                laserpow = self._power(pixel, args["maxpower"], args["poweroffset"])

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


def loadImage(args: Namespace) -> NDArray[Shape["*,*"], UInt8]:
    """
    loadimage: load an image and convert it to b&w and white background
    """

    if args.image:
        # add alpha channel
        img = Image.open(args.image.name).convert("RGBA")

        # create a white background and add it to the image
        img_background = Image.new(mode = "RGBA", size = img.size, color = (255,255,255))
        img = Image.alpha_composite(img_background, img)

        if args.size is not None:
            # convert image to black&white (without alpha) and requested size
            img = img.resize((int(args.size[0]/args.pixelsize),
                              int(args.size[1]/args.pixelsize)), Image.Resampling.LANCZOS).convert("L")
        else:
            # convert image to black&white
            # Note that the image keeps its resolution (same number of pixels for x and y-axis)
            #  each image pixel is converted to a gcode move of pixelsize length
            img = img.resize(img.size, Image.Resampling.LANCZOS).convert("L")

        if args.showimage:
            img.show()

        # return np array of image
        return np.array(img)

    return None

def main() -> int:
    """
    main
    """
    # defaults
    pixelsize_default = 0.1
    speed_default = 800
    power_default = 300
    poweroffset_default = 0
    speedmoves_default = 10
    noise_default = 0
    overscan_default = 0

    # Define command line argument interface
    parser = argparse.ArgumentParser(description='Convert an image to gcode for GRBL v1.1 compatible diode laser engravers,\n'
                                                 ' each image pixel is converted to a gcode move of pixelsize length.'
                                     , formatter_class=argparse.RawTextHelpFormatter )
    parser.add_argument('image', type=argparse.FileType('r'), help='image file to be converted to gcode')
    parser.add_argument('gcode', type=argparse.FileType('w'), nargs='?', default = sys.stdout, help='gcode output')
    parser.add_argument('--showimage', action='store_true', default=False, help='show b&w converted image' )
    parser.add_argument('--pixelsize', default=pixelsize_default, metavar="<default:" + str(pixelsize_default)+">",
        type=float, help="pixel size in mm (XY-axis): each image pixel is drawn this size")
    parser.add_argument('--speed', default=speed_default, metavar="<default:" + str(speed_default)+">",
        type=int, help='draw speed in mm/min')
    parser.add_argument('--maxpower', default=power_default, metavar="<default:" +str(power_default)+ ">",
        type=int, help="maximum laser power while drawing (as a rule of thumb set to 1/3 of the maximum of a machine having a 5W laser)")
    parser.add_argument('--poweroffset', default=poweroffset_default, metavar="<default:" +str(poweroffset_default)+ ">",
        type=int, help="pixel intensity to laser power: shift power range [0-maxpower]")
    parser.add_argument('--size', default=None, nargs=2, metavar=('gcode-width', 'gcode-height'),
        type=float, help="target gcode width and height in mm (default: not set and determined by pixelsize and image source resolution)")
    parser.add_argument('--offset', default=None, nargs=2, metavar=('X-off', 'Y-off'),
        type=float, help="laser drawing starts at offset in mm (default not set, --center cannot be set at the same time)")
    parser.add_argument('--center', action='store_true', default=False, help='set origin at the image center (--offset cannot be set at the same time)' )
    parser.add_argument('--speedmoves', default=speedmoves_default, metavar="<default:" + str(speedmoves_default)+">",
        type=float, help="length of zero burn zones in mm (0 sets no speedmoves): issue speed (G0) moves when skipping space of given length (or more)")
    parser.add_argument('--noise', default=noise_default, metavar="<default:" +str(noise_default)+ ">",
        type=int, help="noise power level, do not burn pixels below this power level")
    parser.add_argument('--overscan', default=overscan_default, metavar="<default:" +str(overscan_default)+ ">",
        type=int, help="overscan image lines to avoid incorrect power levels for pixels at left and right borders, number in pixels, default off")
    parser.add_argument('--constantburn', action='store_true', default=False, help='select constant burn mode M3 (a bit more dangerous!), instead of dynamic burn mode M4')
    parser.add_argument('--validate', action='store_true', default=False, help='validate gcode file, do inverse and show image result' )
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__, help="show version number and exit")

    args = parser.parse_args()

    # check incompatible arguments
    if args.validate and (args.gcode.name == "<stdout>" or not GCODE2IMAGE):
        if not GCODE2IMAGE:
            print("For validation package gcode2image.py must be installed (in $PATH or python install path)")
        else:
            print("For validation a 'gcode filename' argument must be set.")
            parser.print_usage(sys.stderr)
        sys.exit(1)

    if args.center and args.offset is not None:
        print("options --center and --offset cannot be combined!")
        sys.exit(1)

    if args.offset is None:
        args.offset = (0.0, 0.0)

    # load and convert image to B&W
    # flip image updown because Gcode and raster image coordinate system differ in this respect
    narr = np.flipud(loadImage(args))

    if args.center:
        args.offset = (-round((narr.shape[1] * args.pixelsize)/2,1), -round((narr.shape[0] * args.pixelsize)/2,1))

    # get program parameters
    params = ''
    for k, v in args.__dict__.items():
        if params != '':
            params += f",\n"
        if hasattr(v, 'name'):
            params += f";      {k}: {os.path.basename(v.name)}"
        else:
            params += f";      {k}: {v}"

    print(f"dict: {args.__dict__.items()}")
    print(f"type args: {type(args.__dict__.items())}")
    print(args.__dict__["pixelsize"])
    print(type(args.__dict__["pixelsize"]))

    # get print area
    print_area = f'print area: {str(round(narr.shape[1] * args.pixelsize,2))}x{str(round(narr.shape[0] * args.pixelsize,2))} mm (XY)\n'

    # show print area
    print(f"{print_area}")

    # on the safe side: laser stop, fan on, laser on while moving
    gcode_header = "M5\n" + "M8\n" + "M3\n" if args.constantburn else "M4\n"
    # laser off, fan off, program stop
    gcode_footer = "M5\n" + "M9\n" + "M2\n"

    # create image conversion object
    convert = Image2gcode()
    # get gcode for image
    image_gc = convert.image2gcode(narr, args.__dict__)

    # header comment
    gcode = (f";    {os.path.basename(sys.argv[0])} {__version__} ({str(datetime.now()).split('.')[0]})\n"
             f";    arguments:\n{params}\n;\n"
             f";    {print_area}")

    # get bounding box for this image
    gcode += f";    {convert.bbox}\n;\n"

    # init gcode
    gcode += "\nG00 G17 G40 G21 G54\n" + "G90\n"

    # emit it all
    print(gcode + gcode_header + image_gc + gcode_footer, file=args.gcode)

    if args.validate:
        args.gcode.close()
        with open(args.gcode.name, "r") as fgcode:
            # flip to raster image coordinate system
            img = np.flipud(gcode2image(Namespace(gcode = fgcode, resolution = args.pixelsize, showG0 = False, showorigin = True, grid = True)))

            # convert to image
            img = Image.fromarray(img)

            # show image
            img.show()

    return 0

if __name__ == '__main__':
    sys.exit(main())
