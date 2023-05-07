# image2gcode
Convert an image to gcode for GRBL v1.1 compatible diode laser engravers.

Diode lasers are fast at switching to different power levels. This makes them ideal to write pixels (with discrete intensity levels) at a relatively fast rate. This program converts image pixels to laser 'pixels' one on one. The laserhead sweeps from left to right and vice versa, with each sweep stepping in the other direction. Images (with or without Alpha channel) are converted to black&white first - laser intensity (burn rate) can be seen as a grayscale - and get a white background. Image pixel intensities are inverted (burnrate is an inverse scale) and translated to gcode commands.
The translation produces dense gcode: pixels with same intensity are drawn with one gcode command and only coordinates and Gcomands that change are writen.

It is important to use images that have a high contrast ratio, because burnlevels have less intensity range. (A future add-on makes it possible to get an image of the produced gcode, as an option, to see the effect before writing it out.)

Installation note: 
Copy this file and run with ```python3 image2gcode.py ```(or ```chmod u+x image2gcode.py``` and run with ```./image2gcode.py``` or just ```image2gcode.py``` when in $PATH)

Example:
```
> image2gcode.py logo.png logo.gc
```
Usage:
```
> image2gcode.py -h
usage: image2gcode.py [-h] [--showimage] [--pixelsize <default:0.1>] [--speed <default:800>] [--power <default:300>] [-V] image [gcode]

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
  --power <default:300>
                        maximum laser power while drawing (as a rule of thumb set to 1/3 of the machine maximum)
  -V, --version         show version number and exit

```                        
                        
