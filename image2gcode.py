#!/usr/bin/env python3
"""
image2gcode: convert an image to gcode.
"""
__version__ = "v1.0.0-beta"

import sys
import argparse
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

    # set printer start coordinates
    X = round(10.0, XY_prec)
    Y = round(10.0, XY_prec)

    # on the safe side: laser stop, fan on, laser on while moving
    gcode_header = ["M5","M8", "M4"]
    # laser off, fan off, program stop
    gcode_footer = ["M5","M9","M2"]

    # header comment
    gcode = [';\n;    ' + sys.argv[0] + " (" + str(datetime.now()).split('.')[0] + ")\n" +
        ';    Print area: ' + str(img.shape[1] * args.pixelsize) + "mm x " + str(img.shape[0] * args.pixelsize) + "mm (XY)\n;\n" ]

    # init gcode
    gcode += ["G00 G17 G40 G21 G54","G90"]
    # on the safe side: laser stop, fan on, laser on while moving only
    gcode += gcode_header

    # set printer start coordinates
    X = round(10.0, XY_prec)
    Y = round(10.0, XY_prec)
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

        # draw this pixel line
        for count, pixel in enumerate(line):
            # power proportional to maximum laser power
            laserpow = round((1.0 - float(pixel/255)) * args.power) if invert_intensity else round(float(pixel/255) * args.power)

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
    parser.add_argument('--power', default=power_default, metavar="<default:" +str(power_default)+ ">",
        type=int, help="maximum laser power while drawing (as a rule of thumb set to 1/3 of the machine maximum)")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__, help="show version number and exit")

    args = parser.parse_args()

    # load and convert image to B&W
    narr = loadImage(args.image.name,args.showimage)

    print('Print area: ' + str(narr.shape[1] * args.pixelsize) + "mm x " + str(narr.shape[0] * args.pixelsize) + "mm (XY)")

    # emit gcode for image
    print(image2gcode(narr, args), file=args.gcode)
    return 0

if __name__ == '__main__':
    sys.exit(main())
