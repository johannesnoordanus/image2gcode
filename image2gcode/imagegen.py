
"""
make test images
"""

import sys
import re
import argparse
import readline
import random
from typing import TextIO
from datetime import datetime
from collections import namedtuple
from enum import Enum
from PIL import Image
import numpy as np

# pip install nptyping[complete]
# https://github.com/ramonhagenaars/nptyping/blob/master/USERDOCS.md#Quickstart
from nptyping import NDArray, UInt8, Shape

__version__ = "0.1.0"

class Orientation(Enum):
    HORIZONTAL = 1
    VERTICAL = 2
    DIAGONAL = 3

def square(img, border = (350,350), offset = (25,25), width = 2, color = 0, filled = False):
    size = (img.shape[1],img.shape[0])
    widthD = max(round(width/2),2)

    if filled:
        for x in range(offset[0],border[0] + offset[0] if (border[0] + offset[0]) <= size[0] else size[0]):
            img[offset[1]:border[1] + offset[1] if (border[1] + offset[1]) <= size[1] else size[1],x] = color

    else:
        # make square border (black, pixel value 0)
        for x in range(0 + offset[0],border[0] + offset[0]):
            img[offset[1]-widthD:widthD + offset[1],x] = color
            img[border[1] + offset[1]-widthD:border[1] + offset[1] + widthD,x] = color

        for y in range(0 + offset[1],border[1] + offset[1]):
            img[y,0 + offset[0] - widthD:widthD + offset[0]] = color
            img[y,border[0] + offset[0]-widthD:border[0] + offset[0] + widthD] = color

def square_pattern(img):
    size = min(img.shape[1],img.shape[0])
    for i in range(size - round(size/20),10,-10):
        square(img, border = (i,i), offset = (round((size - i)/2),round((size - i)/2)), width = 1)

def square_random(img):
    size = (img.shape[1],img.shape[0])
    i = round(min(size[0], size[1]) * random.random()/4)
    for x in range(0,i):
        newborder = (round((size[0] - 11) * random.random()),round((size[1] - 11) * random.random()))
        square(img, border = (newborder[0],newborder[1]),
             offset = (round((size[0] - newborder[0]) * random.random()),round((size[1] - newborder[1]) * random.random())),
             width = round(20 * random.random()), color = round(255 * random.random()))

def grid(img, grid_spacing = 10, width = 2, color = 0):
    size = (img.shape[1],img.shape[0])
    widthD = max(round(width/2),2)
    # make grid grid_spacing x grid_spacing pixels
    # draw grid X lines
    for i in range(round(size[0]%grid_spacing), size[0], round(size[0]/grid_spacing)):
        img[:,i-widthD:i+widthD] = color
    # draw grid Y lines
    for i in range(round(size[1]%grid_spacing), size[1], round(size[1]/grid_spacing)):
        img[i-widthD:i+widthD,:] = color

def raster_1_pixel(img, orientation = Orientation.HORIZONTAL.value, color = 0):
    size = (img.shape[1],img.shape[0])
    if orientation == Orientation.HORIZONTAL.value:
        for i in range(0, size[0], 2):
            img[:,i] = color

    elif orientation == Orientation.VERTICAL.value:
        for i in range(0, size[1], 2):
            img[i,:] = color

    elif orientation == Orientation.DIAGONAL.value:
        size = min(size[0],size[1])
        for i in range(0,size,3):
            for p in range(i,size):
                img[p,p-i] = color
                img[p-i,p] = color

def line(img, start = (0,0), end = (20,10), width = 2, color = 0):
    widthD = max(round(width/2),2)
    if abs(end[0] - start[0]):
        yD = (end[1] - start[1])/abs(end[0] - start[0])
        y = start[1]
        for x in range(start[0], end[0], 1 if start[0] <= end[0] else -1 ):
            img[y - widthD:y + widthD,x - widthD:x + widthD] = color
            y = round(start[1] + abs(x-start[0])*yD)

def line_random(img):
    size = (img.shape[1],img.shape[0])
    i = round(min(size[0], size[1]) * random.random())
    nstart = (round((size[0] - 6) * random.random()),round((size[1] - 6) * random.random()))
    for x in range(0,i):
        nend = (round((size[0] - 6) * random.random()),round((size[1] - 6) * random.random()))
        line(img, start = nstart, end = nend, width = round(10 * random.random()), color = round(255 * random.random()))
        nstart = nend

def pixel(img, position = (0,0), width = 2, color = 0):
    widthD = max(round(width/2),2)
    size = (img.shape[1],img.shape[0])
    img[position[1]:position[1],position[0]:position[0]] = color
    img[round(position[1] - widthD):round(position[1] + widthD),round(position[0] - widthD):round(position[0] + widthD)] = color

def pixel_random(img):
    size = (img.shape[1],img.shape[0])
    i = round(min(size[0], size[1]) * random.random())
    for x in range(0,i):
        pixel(img, position = (round((size[0] - 11) * random.random()),round((size[1] - 11) * random.random())),
              width = round(20 * random.random()), color = round(255 * random.random()))

def gradient(img, orientation = Orientation.HORIZONTAL.value):
    size = (img.shape[1],img.shape[0])
    if orientation == Orientation.HORIZONTAL.value:
        # horizontal gradient
        for x in range(0,size[0]):
            for y in range(0,size[1]):
                img[y,x] = round(x * float(255/size[0]))

    elif orientation == Orientation.VERTICAL.value:
        # vertical gradient
        for y in range(0,size[1]):
            for x in range(0,size[0]):
                img[y,x] = round(y * float(255/size[1]))

    elif orientation == Orientation.DIAGONAL.value:
        size = min(size[0],size[1])
        for i in range(0,size):
            for p in range(i,size):
                img[p,p-i] = round((size + i) * float(255/(2 * size)))
                img[p-i,p] = round( (size - i) * float(255/(2 * size)))

    elif orientation > Orientation.DIAGONAL.value:
        discrete = orientation
        discreteD = max(round(discrete/2),2)
        # horizontal gradient
        for x in range(0,size[0],discrete):
            for y in range(0,size[1]):
                img[y,max(x-discreteD,0):min(x+discreteD,size[0])] = round(x * float(255/size[0]))

def border(img, width = 2):
        size = (img.shape[1],img.shape[0])
        hwidth = max(round(width/2),2)
        square(img, border = (size[0] - width,size[1] - width), offset = (hwidth,hwidth), width = width, color = 0)

def create_image(size = (400,400)) -> NDArray[Shape["*,*"], UInt8]:

    # black background
    #image = np.zeros([iheight + 1, iwidth + 1], dtype=np.uint8)

    # create image array (hight,width), white backround and unsigned 8 bit elements
    return np.full([size[1], size[0]], 255, dtype=np.uint8)

def gen_images(size = (400,400), showimage = False, write = False):
    """
    make test images
    """

    # create image array
    img = create_image(size)
    gradient(img, orientation = Orientation.HORIZONTAL.value)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"gradient_{Orientation.HORIZONTAL.name.lower()}_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    gradient(img, orientation = Orientation.VERTICAL.value)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"gradient_{Orientation.VERTICAL.name.lower()}_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    gradient(img, orientation = Orientation.DIAGONAL.value)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"gradient_{Orientation.DIAGONAL.name.lower()}_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    gradient(img, orientation = round(min(size[0],size[1])/10))
    pic = Image.fromarray(img)
    if write:
        pic.save(f"gradient_banding_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    raster_1_pixel(img, orientation = Orientation.HORIZONTAL.value, color = 0)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"raster_1_pixel_{Orientation.HORIZONTAL.name.lower()}_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    raster_1_pixel(img, orientation = Orientation.VERTICAL.value, color = 0)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"raster_1_pixel_{Orientation.VERTICAL.name.lower()}_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    raster_1_pixel(img, orientation = Orientation.DIAGONAL.value, color = 0)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"raster_1_pixel_{Orientation.DIAGONAL.name.lower()}_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    square_pattern(img)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"squarepattern_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    square(img, filled = True)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"squarefilled_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    border(img, width = 4)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"border_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    grid(img, grid_spacing = 10, width = 2, color = 0)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"grid_{size[0]}x{size[1]}_pixels.png")
    if showimage:
        pic.show()

    img = create_image(size)
    square_random(img)
    pic = Image.fromarray(img)
    if write:
        pic.save(f"easter_{size[0]}x{size[1]}_egg.png")
    if showimage:
        pic.show()

def main():
    """
    main
    """

    size_default = (400,400)

    # Define command line argument interface
    parser = argparse.ArgumentParser(description='test image generator', formatter_class=argparse.RawTextHelpFormatter )
    parser.add_argument('image', type=argparse.FileType('w'),nargs='?', help='calibration image file name')
    parser.add_argument('--showimage', action='store_true', default=False, help="show generated image(s)")
    parser.add_argument('--size', default=size_default, nargs=2, metavar=('pixel-width', 'pixel-height'),
        type=int, help="create a test image of this size (in pixels)")
    parser.add_argument('--square', default=None, nargs=7, metavar=('border-width', 'border-height', 'offset-X', 'offset-Y', 'line-width', 'color', 'filled'),
        type=int, help="generate a (filed) square of size (border widthxheight), color and linewidth at offset (X,Y)")
    parser.add_argument('--pixel', default=None, nargs=4, metavar=('X', 'Y', 'size', 'color'),
        type=int, help="generate a pixel of given size and color at (X,Y)")
    parser.add_argument('--line', default=None, nargs=6, metavar=('startX', 'startY', 'endX', 'endY', 'line-width', 'color'),
        type=int, help="generate a line from start (XY) to end (XY) of given width and color")
    parser.add_argument('--grid', default=None, nargs=3, metavar=('spacing', 'line-width', 'color' ),
        type=int, help="generate a grid of lines of given size, color and spacing")
    parser.add_argument('--raster', default=None, nargs=2, metavar=('orientation', 'color' ),
        type=int, help="generate a 1 pixel raster of given orientation and color")
    parser.add_argument('--gradient', default=None, nargs=1, metavar=('orientation'),
        type=int, help=f"generate a gradient in horizontal({Orientation.HORIZONTAL.value}), vertical({Orientation.VERTICAL.value})"
                       f" or diagonal({Orientation.DIAGONAL.value}) direction or horizontal banding of (>{Orientation.DIAGONAL.value}) pixels wide")
    parser.add_argument('--random', action='store_true', default=False, help='show random pixels, squares, lines, depending on the option (--pattern cannot be set)')
    parser.add_argument('--pattern', action='store_true', default=False, help='show pattern of squares (future other image elements) (--random cannot be set)')
    parser.add_argument('--border', default=None, nargs=1, metavar=('width'),type=int, help='add an image border of given width' )
    parser.add_argument('--genimages', action='store_true', default=False, help="write a set of test (calibration) images to the file system")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__, help="show version number and exit")

    args = parser.parse_args()

    if args.random and args.pattern:
        print("cannot set '--args.random' and '--args.pattern' at the same time: exit")
        sys.exit(1)

    if args.genimages:
        gen_images(size = (args.size[0], args.size[1]), showimage = args.showimage, write = False if args.showimage is None else True)
        print("Generated calibration images: all other options are ignored " + (
              "(option --showimage is set: images are not written to the file system)" if args.showimage else "(except --showimage)") + ", exit")
        sys.exit(1)

    # create image array
    img = create_image(args.size)

    if args.square:
        if args.random:
            square_random(img)
        elif args.pattern:
            square_pattern(img)
        else:
            s = args.square
            square(img, border = (s[0],s[1]), offset = (s[2],s[3]), width = s[4], color = s[5], filled = True if s[6] else False)

    if args.grid:
        g = args.grid
        grid(img, grid_spacing = g[0], width = g[1], color = g[2])

    if args.pixel:
        if args.random:
            pixel_random(img)
        else:
            p = args.pixel
            pixel(img, position = (p[0],p[1]), width = p[2], color = p[3])

    if args.gradient:
        g = args.gradient
        gradient(img, orientation = g[0])

    if args.raster:
        r = args.raster
        raster_1_pixel(img, orientation = r[0], color = r[1])

    if args.line:
        if args.random:
            line_random(img)
        else:
            l = args.line
            line(img, start = (l[0],l[1]), end = (l[2],l[3]), width = l[4], color = l[5])

    if args.border:
        border(img, width = args.border[0])

    # convert to image
    pic = Image.fromarray(img)

    # show image
    if args.showimage:
        pic.show()

    # write image file
    if args.image:
        pic.save(args.image.name)

if __name__ == '__main__':
    sys.exit(main())


