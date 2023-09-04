# image2gcode
Convert an image to gcode for GRBL v1.1 compatible diode laser engravers. 

Diode lasers are fast at switching to different power levels. This makes them ideal to write pixels (with discrete intensity levels) at a relatively fast rate.

This program converts each image pixel to a gcode move of *--pixelsize* length - one on one.
Images (with or without Alpha channel) are converted to black&white first - laser intensity (burn rate) can be seen as a grayscale - and get a white background. 
Image pixel intensities are inverted (burnrate is an inverse scale) and translated to gcode ```move``` commands. Note that the image to convert is unaltered in all other aspects and keeps its pixel dimensions!

Conversion produces optimized gcode: pixels with same intensity are drawn with one gcode ```move``` command and only coordinates and gcode comands that change are writen.
Images are drawn in a scan line way: the laserhead sweeps from left to right and vice versa, with each sweep stepping in the other direction, but images are drawn within their outline only and background (white) is skipped at maximum speed between image 'zones'. See options *--speedmoves* and *--noise*.

It is possible to validate the gcode produced in one go: its size, placement and pixel burnlevels are visible with switch ```--validate```. Further information can be obtained by looking at the header of the gcode file produced.

Note that to get great engravings it is important to use source images that have a high contrast ratio, because burnlevels have less intensity range. To get an engraving the right size, make sure images have enough pixels.
For example if your machines laser width is 0.08mm I would recomment using a pixel size of 0.1mm; an engraving of 50x65 mm^2 (*width*x*height*) will need the source image resolution to be 500x650 pixels (*width*x*height*) in this case.
It is also possible to set the DPI of an image to be exported from Inkscape (for example) and so get the right resolution for your laser machine. In this case the image to be exported should have a DPI setting of 254 (one inch is 25.4mm/0.1 = 254), note the image size when you do the export, because that will be exacly what you get on the laser machine!

If this is too cumbersome, use option --size (release 2.5.0 or above), also for conveniance, to get the origin at the center, set --center. Note that --size will make a conversion of the source image.

Some people noticed incorrect low burn levels at the edges of objects within an image, this can be remedied by using option '--overscan <nbr of pixels>'. This makes sure the laser head will continue for a few pixels on a line after the last non empty pixel, or start the head a few pixels before the first non empty pixel is written on a line.


To summarize:

Optimized gcode
- draw pixels in one go until change of power
- emit X/Y coordinates only when they change
- emit linear move 'G1/G0' code minimally
- does not emit zero power (or below cutoff) pixels

General optimizations
- laser head has defered and sparse moves.
(XY locations are virtual, head does not always follow)
- moves at high speed (G0) over 10mm (default) or more zero pixels
- low burn levels (stray pixels) can be suppressed (default off)
- overscan a line to make sure burnlevels at the edges of objects are perfect (default off)

### Install
Depends on python libraries *numpy*, *PIL* and (inverse function) *gcode2image* (https://github.com/johannesnoordanus/gcode2image/)
```
> pip install image2gcode

Note: on Manjaro it is 'pipx' now!
```
### Example:
```
[somedir]> image2gcode --maxpower 300 --showimage --speedmoves 5 --noise 5 --validate test.png test.gc
```

This command generates a gcode file 'test.gc' from an image 'test.png'. It burns pixels - .1mm^2 default - 
at a maximum of 300 (which level is laser machine dependend).
Option *--showimages* starts an image viewer containing the original image in B&W and added white background 
(when transparent) and option --validate shows the resulting image via an inverse function - gcode2image - 
to be able to verify the gcode file. 
Option *--speedmove 5* generates a maximum speed moves (G0) for non burn zones which (can) speed up engravings 
significantly. 
Option *--noise 5* omits all pixels having burn values of 5 or less, this can remove noise (stray pixels) from some images. 

The result file 'test.gc' contains highly optimized gcodes (the file is of minimal length) and gcodes run a minimal path.

### Usage:
```
> image2gcode --help
usage: image2gcode_overscan.py [-h] [--showimage] [--pixelsize <default:0.1>] [--speed <default:800>] [--maxpower <default:300>]
                               [--size gcode-width gcode-height] [--offset X-off Y-off] [--center] [--speedmoves <default:10>]
                               [--noise <default:0>] [--overscan <default:0>] [--constantburn] [--validate] [-V]
                               image [gcode]

Convert an image to gcode for GRBL v1.1 compatible diode laser engravers,
 each image pixel is converted to a gcode move of pixelsize length.

positional arguments:
  image                 image file to be converted to gcode
  gcode                 gcode output

options:
  -h, --help            show this help message and exit
  --showimage           show b&w converted image
  --pixelsize <default:0.1>
                        pixel size in mm (XY-axis): each image pixel is drawn this size
  --speed <default:800>
                        draw speed in mm/min
  --maxpower <default:300>
                        maximum laser power while drawing (as a rule of thumb set to 1/3 of the maximum of a machine having a 5W laser)
  --size gcode-width gcode-height
                        target gcode width and height in mm (default: not set and determined by pixelsize and image source resolution)
  --offset X-off Y-off  laser drawing starts at offset in mm (default not set, --center cannot be set at the same time)
  --center              set origin at the image center (--offset cannot be set at the same time)
  --speedmoves <default:10>
                        length of zero burn zones in mm (0 sets no speedmoves): issue speed (G0) moves when skipping space of given length (or more)
  --noise <default:0>   noise power level, do not burn pixels below this power level
  --overscan <default:0>
                        overscan image lines to avoid incorrect power levels for pixels at left and right borders, number in pixels, default off
  --constantburn        select constant burn mode M3 (a bit more dangerous!), instead of dynamic burn mode M4
  --validate            validate gcode file, do inverse and show image result
  -V, --version         show version number and exit

```                        
