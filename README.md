# image2gcode
Convert an image to gcode for GRBL v1.1 compatible diode laser engravers.

Diode lasers are fast at switching to different power levels. This makes them ideal to write pixels (with discrete intensity levels) at a relatively fast rate. This program converts image pixels to laser 'pixels' one on one. The laserhead sweeps from left to right and vice versa, with each sweep stepping in the other direction. Images (with or without Alpha channel) are converted to black&white first - laser intensity (burn rate) can be seen as a grayscale - and get a white background. Image pixel intensities are inverted (burnrate is an inverse scale) and translated to gcode commands.
The translation produces dense gcode: pixels with same intensity are drawn with one gcode command and only coordinates and Gcomands that change are writen.
Note that option```--validate```makes it possible to validate the gcode (result) file (this is inverse conversion gcode2image).

It is important to use images that have a high contrast ratio, because burnlevels have less intensity range.

Installation note: 
Copy this file and run with ```python3 image2gcode.py ```(or ```chmod u+x image2gcode.py``` and run with ```./image2gcode.py``` or just ```image2gcode.py``` when in $PATH)

### Install
Depends on python libraries numpy, PIL (pip install ..).
Depends on inverse function gcode2image.py ```--validate```option.</br>
Should be 'installed' in $PATH or python path.
(Download from https://github.com/johannesnoordanus/gcode2image/tree/main)

Download 'image2gcode.py' and 'install' to a directory within $PATH (or within python path).</br>
Then:
```
> cd <above dir>
> chmod u+x image2gcode.py    # to make it executable; thats it!
```
### Example:
```
> image2gcode.py logo.png logo.gc
```
### Usage:
```
> image2gcode.py -h
usage: image2gcode.py [-h] [--showimage] [--pixelsize <default:0.1>] [--speed <default:800>] [--maxpower <default:300>] [--offset X-off Y-off] [--validate] [-V] image [gcode]

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
                        maximum laser power while drawing (as a rule of thumb set to 1/3 of the machine maximum)
  --offset X-off Y-off  laser drawing starts at offset (default: X10.0 Y10.0)
  --validate            validate gcode file, do inverse and show image result
  -V, --version         show version number and exit

```                        
                        
