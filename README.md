# image2gcode
Convert an image to gcode for GRBL v1.1 compatible diode laser engravers.

Diode lasers are fast at switching to different power levels. This makes them ideal to write pixels (with discrete intensity levels) at a relatively fast rate. This program converts image pixels to laser 'pixels' one on one. The laserhead sweeps from left to right and vice versa, with each sweep stepping in the other direction. Images (with or without Alpha channel) are converted to black&white first - laser intensity (burn rate) can be seen as a grayscale - and get a white background. Image pixel intensities are inverted (burnrate is an inverse scale) and translated to gcode commands.
The translation produces dense gcode: pixels with same intensity are drawn with one gcode command and only coordinates and Gcomands that change are writen.
Note that option```--validate```makes it possible to validate the gcode (result) file (this is inverse conversion gcode2image).

It is important to use images that have a high contrast ratio, because burnlevels have less intensity range.

Version 2.0.0 has important new speed optimizations. Engravings run significantly faster and skip from one image zone to the other at maximum speed. See options ```--speedmoves``` and ```--noise``` for example.

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

### Install
Depends on python libraries *numpy*, *PIL* and (inverse function) *gcode2image* (https://github.com/johannesnoordanus/gcode2image/)
```
> pip install gcode2image
> pip install image2gcode
>

Note: on Manjaro it is 'pipx' now!
```
### Example:
```
[somedir]> image2gcode --maxpower 300 --showimage --speedmoves 5 --noise 5 --validate test.png test.gc

This command generates a gcode file 'test.gc' from an image 'test.png'. It burns pixels - .1mm^2 default - at a maximum of 300 (which level is laser machine dependend).
Option --showimages starts an image viewer containing the original image in B&W and added white background (when transparent) and option --validate shows the resulting image via an inverse function - gcode2image - to be able to verify the gcode file. 
Option --speedmove 5 generates a maximum speed moves (G0) for non burn zones which (can) speed up engravings significantly. Option --noise 5 omits all pixels having burn values of 5 or less, this can remove noise (stray pixels) from some images. 
The result file 'test.gc' contains highly optimized gcodes (the file is of minimal length) and gcodes run a minimal path.
```
### Usage:
```
[somedir]> image2gcode --help
usage: image2gcode [-h] [--showimage] [--pixelsize <default:0.1>] [--speed <default:800>] [--maxpower <default:300>] [--offset X-off Y-off] [--speedmoves <default:10>]
                   [--noise <default:0>] [--validate] [-V]
                   image [gcode]

Convert an image to gcode for GRBL v1.1 compatible diode laser engravers.

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
  --offset X-off Y-off  laser drawing starts at offset (default: X10.0 Y10.0)
  --speedmoves <default:10>
                        length of zero burn zones in mm (0 sets no speedmoves): issue speed (G0) moves when skipping space of given length (or more)
  --noise <default:0>   noise power level, do not burn pixels below this power level
  --validate            validate gcode file, do inverse and show image result
  -V, --version         show version number and exit

```                        
