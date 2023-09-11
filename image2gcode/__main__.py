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

# pip install nptyping[complete]
# https://github.com/ramonhagenaars/nptyping/blob/master/USERDOCS.md#Quickstart
from nptyping import NDArray, UInt8, Shape

from image2gcode import __version__
from image2gcode.image2gcode import Image2gcode

GCODE2IMAGE = True
try:
    from gcode2image import gcode2image
except ImportError:
    GCODE2IMAGE = False

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
    parser.add_argument('--showoverscan', action='store_true', default=False, help='show overscan pixels (note that this is visible and part of the gcode emitted!)' )
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

    # get print area
    print_area = f'print area: {str(round(narr.shape[1] * args.pixelsize,2))}x{str(round(narr.shape[0] * args.pixelsize,2))} mm (XY)'

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
             f";    {print_area}\n")

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
