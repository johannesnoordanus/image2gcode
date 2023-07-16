#!/usr/bin/env python3
"""
image2gcode: convert an image to gcode.
"""
__version__ = "1.2.0"

import sys
import argparse
from argparse import Namespace
from datetime import datetime
from PIL import Image
import numpy as np

GCODE2IMAGE = True
try:
    from gcode2image import gcode2image
except ImportError:
    GCODE2IMAGE = False

def loadImage(imagefile: str = None, showimage: bool = True):
    """
    loadimage: load an image and convert it to b&w with white background
    """

    if imagefile:
        # add alpha channel
        img = Image.open(imagefile).convert("RGBA")

        # create a white background and add it to the image
        img_background = Image.new(mode = "RGBA", size = img.size, color = (255,255,255))
        img = Image.alpha_composite(img_background, img)

        # convert image to black&white (same size)
        img = img.resize(img.size, Image.Resampling.LANCZOS).convert("L")
        if showimage:
            img.show()

        # return np array of image
        return np.array(img)

    return None

def image2gcode(img, args) -> str:
    """
    image2gcode: convert image to gcode
    """

    # args settings:
    # pixelsize:        pixel size in mm (all dimensions)
    # speed:            laser head print speed
    # power:            maximum power of laser

    invert_intensity = True		# black == white

    # set X/Y-axis precision to number of digits after
    XY_prec = len(str(args.pixelsize).split('.')[1])

    # on the safe side: laser stop, fan on, laser on while moving
    gcode_header = ["M5","M8", "M4"]
    # laser off, fan off, program stop
    gcode_footer = ["M5","M9","M2"]

    # header comment
    gcode = [';\n;    ' + sys.argv[0] + " " +  __version__ + " (" + str(datetime.now()).split('.')[0] + ")\n" +
        ';    Area: ' + str(round(img.shape[1] * args.pixelsize,2)) + "mm x " + str(round(img.shape[0] * args.pixelsize,2)) + "mm (XY)" +
        ';    > pixelsize ' + str(args.pixelsize) + ' mm^2, speed ' + str(args.speed) + ' mm/min, maxpower ' + str(args.maxpower) + ', offset ' + str(args.offset) + "\n;\n" ]

    # init gcode
    gcode += ["G00 G17 G40 G21 G54","G90"]
    # on the safe side: laser stop, fan on, laser on while moving only
    gcode += gcode_header

    # set printer start coordinates
    X = round(args.offset[0], XY_prec)
    Y = round(args.offset[1], XY_prec)

    # go to start
    gcode += [f"G0X{X}Y{Y}"]

    # set write speed and G1 move mode
    # (note that this stays into effect until another G code is executed,
    #  so we do not have to repeat this for all coordinates emitted below)
    gcode += [f"G1F{args.speed}"]

    # Print left to right, right to left (etc.)
    # Optimized gcode:
    # - draw pixels until change of power
    # - emit X/Y coordinates only when they change
    # - emit linear move 'G1' code only once
    # - does not emit in between spaces
    #
    left2right = True

    # start print
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
            laserpow = round((1.0 - float(pixel/255)) * args.maxpower) if invert_intensity else round(float(pixel/255) * args.maxpower)

            # delay emit first pixel (so all same power pixels can be emitted in one sweep)
            if count == 0:
                prev_pow = laserpow

            # draw pixels until change of power
            if laserpow != prev_pow or count == line.size-1:
                code = f"X{X}"
                code += f"S{prev_pow}"
                gcode += [code]
                if count == line.size-1:
                    continue
                prev_pow = laserpow # if laserpow != prev_pow

            # next point
            X = round(X + (args.pixelsize if left2right else -args.pixelsize), XY_prec)

        # go to next scan line
        Y = round(Y + args.pixelsize, XY_prec)
        gcode += [f"Y{Y}S0"]

        # change print direction
        left2right = not left2right

    # laser off, fan off, program stop
    gcode += gcode_footer

    return '\n'.join(gcode)

def main() -> int:
    """
    main
    """
    # defaults
    pixelsize_default = 0.1
    speed_default = 800
    power_default = 300

    # Define command line argument interface
    parser = argparse.ArgumentParser(description='Convert an image to gcode for GRBL v1.1 compatible diode laser engravers.')
    parser.add_argument('image', type=argparse.FileType('r'), help='image file to be converted to gcode')
    parser.add_argument('gcode', type=argparse.FileType('w'), nargs='?', default = sys.stdout, help='gcode output')
    parser.add_argument('--showimage', action='store_true', default=False, help='show b&w converted image' )
    parser.add_argument('--pixelsize', default=pixelsize_default, metavar="<default:" + str(pixelsize_default)+">",
        type=float, help="pixel size in mm (XY-axis): each image pixel is drawn this size")
    parser.add_argument('--speed', default=speed_default, metavar="<default:" + str(speed_default)+">",
        type=int, help='draw speed in mm/min')
    parser.add_argument('--maxpower', default=power_default, metavar="<default:" +str(power_default)+ ">",
        type=int, help="maximum laser power while drawing (as a rule of thumb set to 1/3 of the machine maximum)")
    parser.add_argument('--offset', default=[10.0, 10.0], nargs=2, metavar=('X-off', 'Y-off'),
        type=float, help="laser drawing starts at offset (default: X10.0 Y10.0)")
    parser.add_argument('--validate', action='store_true', default=False, help='validate gcode file, do inverse and show image result' )
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__, help="show version number and exit")

    args = parser.parse_args()

    if args.validate and (args.gcode.name == "<stdout>" or not GCODE2IMAGE):
        if not GCODE2IMAGE:
            print("For validation package gcode2image.py must be installed (in $PATH or python install path)")
        else:
            print("For validation a 'gcode filename' argument must be set.")
            parser.print_usage(sys.stderr)
        sys.exit(1)

    # load and convert image to B&W
    # flip image updown because Gcode and raster image coordinate system differ
    narr = np.flipud(loadImage(args.image.name,args.showimage))

    print('Area: ' + str(round(narr.shape[1] * args.pixelsize,2)) + "mm x " + str(round(narr.shape[0] * args.pixelsize,2)) + "mm (XY)")
    print('> pixelsize', args.pixelsize, 'mm^2, speed', args.speed, 'mm/min, maxpower ' + str(args.maxpower) + ', offset', args.offset)

    # emit gcode for image
    print(image2gcode(narr, args), file=args.gcode)

    if args.validate:
        args.gcode.close()
        with open(args.gcode.name, "r") as fgcode:
            # flip to raster image coordinate system
            img = np.flipud(gcode2image(Namespace(gcode = fgcode, offset = False, showG0 = True, grid = False)))

            # convert to image
            img = Image.fromarray(img)

            # show image
            img.show()
            # write image file (png)
            #pic.save(args.gcode.name.split('.')[0] + '_' + sys.argv[0].split('.')[0] + '.png')

    return 0

if __name__ == '__main__':
    sys.exit(main())
