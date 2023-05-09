#!/usr/bin/env python3
"""
image2gcode: convert an image to gcode.
"""
__version__ = "v1.0.0-beta"

import sys
import re
import argparse
from typing import TextIO
from datetime import datetime
from PIL import Image
import numpy as np

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

def gcode2image(gcode: TextIO, dimensions, args) -> np.array:
    """
    Convert gcode (file) to image.
    """
    iheight, iwidth = dimensions
    S_max = args.maxpower

    invert_intensity = True

    def pixel_intensity(S: int = None) -> int:
        # pixel intensity (inverse) proportional to laser power
        return round((1.0 - float(S/S_max)) * 255) if invert_intensity else round(float(S/S_max) * 255)

    def set_coordinates(X: int = None, Y: int = None, S: int = None):
        nonlocal x
        nonlocal y
        if X is not None :
            if x == X:
                # this should not happen!
                #raise ValueError(f"Linear move should not go to the same location on a line: ({x},{y}) -> ({X},{y})")
                print(f"Linear move should not go to the same location on a line: ({x},{y}) -> ({X},{y})")
                return

            # Note that (laser) drawing from a point to a point differs from setting a point (within an image):
            #              0   1   2   3   4   5   6     <-- gcode drawing points
            # one line:    |[0]|[1]|[2]|[3]|[4]|[5]|     <-- image pixels
            #
            # For example: drawing from X0 to X2 with value S10 corresponds to setting [0] = S10 and [1] = S10
            # Note also that drawing form left to right differs subtly from the reverse

            # set point intensity value
            if x < X:
                # draw from left to right, note the range (interval): [x,X)
                for x_coord in range(x,X):
                    image[y - start_Y, x_coord - start_X] = pixel_intensity(S)
                    #print("[", x_coord - start_X, ",", y - start_Y, "] = ", "(", S, ")", pixel_intensity(S))
            else:
                # draw from right to left, note the range (interval): [X,x)
                for x_coord in range(X,x):
                    image[y - start_Y, x_coord - start_X] = pixel_intensity(S)
                    #print("[", x_coord - start_X, ",", y - start_Y, "] = ", "(", S, ")", pixel_intensity(S))
            # set current x
            x = X
        if Y is not None:
            # go to next line
            #y = Y-start_Y
            y = Y

    def XY() -> str:
        nonlocal gcode
        nonlocal last_S
        # find next XY-goto coordinate line
        line = gcode.readline()
        if line != '' and not 'G0' in line:
            if "X" in line or "Y" in line:
                # get X (and S) or get Y (until /n)
                X = re.search("X[0-9]+\.[0-9]+",line)
                Y = re.search("Y[0-9]+\.[0-9]+",line)
                S = re.search("S[0-9]+",line)
                if S:
                    S = int(S.group(0)[1:])
                    last_S = S
                else:
                    S = last_S
                if X:
                    # get X coordinate,
                    # get S,
                    X = round(float(X.group(0)[1:])/args.pixelsize)
                    set_coordinates(X = X, S = S)
                if Y:
                    Y = round(float(Y.group(0)[1:])/args.pixelsize)
                    set_coordinates(Y = Y)
        return line
    #
    # setup/init

    # create image array (hight,width) with unsigned 8 bit elements
    image = np.full([iheight, iwidth], 255, dtype=np.uint8)

    # gcode modes stay untill changed
    last_S = None

    # offset (X,Y)
    start_X = round(float(args.offset[0])/args.pixelsize)
    start_Y = round(float(args.offset[1])/args.pixelsize)
    # current (x,y)
    x = start_X
    y = start_Y

    # repeat until EOF
    #     find next XY coordinate and set corresponding image pixel(s) (inverse) intensity
    line = XY()
    while line != '':
        line = XY()

    return image

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
    gcode = [';\n;    ' + sys.argv[0] + " (" + str(datetime.now()).split('.')[0] + ")\n" +
        ';    Print area: ' + str(img.shape[1] * args.pixelsize) + "mm x " + str(img.shape[0] * args.pixelsize) + "mm (XY)\n" +
        ';    Settings: pixelsize ' + str(args.pixelsize) + ' mm^2, speed ' + str(args.speed) + ' mm/min, maxpower ' + str(args.maxpower) + ', offset ' + str(args.offset) + "\n;\n" ]

    # init gcode
    gcode += ["G00 G17 G40 G21 G54","G90"]
    # on the safe side: laser stop, fan on, laser on while moving only
    gcode += gcode_header

    # set printer start coordinates
    X = round(args.offset[0], XY_prec)
    Y = round(args.offset[1], XY_prec)

    # go to start
    gcode += [f"G0 X{X} Y{Y}"]

    # set write speed and G1 move mode
    # (note that this stays into effect until another G code is executed,
    #  so we do not have to repeat this for all coordinates emitted below)
    gcode += [f"G1 F{args.speed}"]

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

        # add line terminator (to make the
        line = np.append(line,0)

        # Note that (laser) drawing from a point to a point differs from setting a point (within an image):
        #              0   1   2   3   4   5   6     <-- gcode drawing points
        # one line:    |[0]|[1]|[2]|[3]|[4]|[5]|     <-- image pixels
        #
        # For example: drawing from X0 to X2 with value S10 corresponds to setting [0] = S10 and [1] = S10
        # Note also that drawing form left to right differs subtly from the reverse

        # draw this pixel line
        for count, pixel in enumerate(line):
            # power proportional to maximum laser power
            laserpow = round((1.0 - float(pixel/255)) * args.maxpower) if invert_intensity else round(float(pixel/255) * args.maxpower)

            # delay emit first pixel (so all same power pixels can be emitted in one sweep)
            if count == 0:
                prev_pow = laserpow

            # draw pixels until change of power
            if laserpow != prev_pow or count == line.size-1:
                code = f"X{X}"
                code += f"S{prev_pow}" if laserpow != prev_pow else ''
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

    # load and convert image to B&W
    narr = loadImage(args.image.name,args.showimage)

    print('Print area: ' + str(narr.shape[1] * args.pixelsize) + "mm x " + str(narr.shape[0] * args.pixelsize) + "mm (XY)")
    print('Settings: pixelsize', args.pixelsize, 'mm^2, speed', args.speed, 'mm/min, maxpower ' + str(args.maxpower) + ', offset', args.offset)

    # emit gcode for image
    print(image2gcode(narr, args), file=args.gcode)

    if args.validate:
        args.gcode.close()
        with open(args.gcode.name, "r") as fgcode:
            img = gcode2image(fgcode, narr.shape, args)

            # convert to image
            img = Image.fromarray(img)

            # show image
            img.show()
            # write image file (jpeg)
            #pic.save(args.gcode.name.split('.')[0] + '_' + sys.argv[0].split('.')[0] + '.jpg')

    return 0

if __name__ == '__main__':
    sys.exit(main())
