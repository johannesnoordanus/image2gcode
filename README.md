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

It is possible to calibrate your laser machine now: option ```--genimages pixel-width pixel-height write``` generates a set calibration files that can be used as input for ```image2gcode``` to experiment with settings like ```--pixelsize```, ```--speed``` and ```--maxpower``` to get the right setup! For example use ```image2gcode --showimage --genimages 200 200 0``` to generate test images of 200 by 200 pixels that show up in the viewer (but are not written to the file system). See chapter *calibrate* below.

Please consider supporting me, so I can make this application better and add new functionality to it: <http://paypal.me/johannesnoordanus/5,00>

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
This command generates a gcode file 'test.gc' from an image 'test.png'.

It burns pixels - .1mm^2 default - at a maximum of 300 (which level is laser machine dependend).

Option *--showimages* starts an image viewer containing the original image in B&W and added white background 
(when transparent) and option --validate shows the resulting image via an inverse function - gcode2image - 
to be able to verify the gcode file. 

Option *--speedmove 5* generates maximum speed moves (G0) for non burn zones which (can) speed up engravings 
significantly. 

Option *--noise 5* omits all pixels having burn values of 5 or less, this can remove noise (stray pixels) from some images. 

The result file 'test.gc' contains highly optimized gcodes (the file is of minimal length) and gcodes run a minimal path.

### Usage:
See notes below.
```
> image2gcode --help
usage: image2gcode [-h] [--showimage] [--pixelsize <default:0.1>] [--speed <default:800>] [--maxpower <default:300>] [--poweroffset <default:0>]
                      [--size gcode-width gcode-height] [--offset X-off Y-off] [--center] [--speedmoves <default:10>] [--noise <default:0>] [--overscan <default:0>]
                      [--showoverscan] [--constantburn] [--validate] [--genimages pixel-width pixel-height write] [-V]
                      [image] [gcode]

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
  --poweroffset <default:0>
                        pixel intensity to laser power: shift power range [0-maxpower]
  --noinvert            do not invert the image
  --size gcode-width gcode-height
                        target gcode width and height in mm (default: not set and determined by pixelsize and image source resolution)
  --offset X-off Y-off  laser drawing starts at offset in mm (default not set, --center cannot be set at the same time)
  --center              set origin at the image center (--offset cannot be set at the same time)
  --speedmoves <default:10>
                        length of zero burn zones in mm (0 sets no speedmoves): issue speed (G0) moves when skipping space of given length (or more)
  --noise <default:0>   noise power level, do not burn pixels below this power level
  --overscan <default:0>
                        overscan image lines to avoid incorrect power levels for pixels at left and right borders, number in pixels, default off
  --showoverscan        show overscan pixels (note that this is visible and part of the gcode emitted!)
  --constantburn        select constant burn mode M3 (a bit more dangerous!), instead of dynamic burn mode M4
  --validate            validate gcode file, do inverse and show image result
  --genimages pixel-width pixel-height write
                        write (when set non zero) 11 calibration images of given pixel size to as much files
  -V, --version         show version number and exit
```
You can also store those settings in ~/.config/image2gcode.toml, eg:
```
pixelsize = 0.1
xmaxtravel = 400
ymaxtravel = 400
imagespeed = 6000
```
It can be used with any parameter which takes a value, and alows to persist your laser settings.

### How to calibrate:
Use a piece of wood that is smooth (sanded) and has a light color tone, a piece of light oak will do fine.  

**Determine pixelsize first**

Each laser machine has a specific beam diameter (width) that can be used as the minimum pixelsize.   
A small width has to be added to prevent pixel overlap when burned. For example a laser having a beam width of 0.08mm should have a pixelsize setting of 0.1mm.
Use calibration files ```raster_1_pixel_horizontal/vertical``` and ```squarefilled``` to find out the right pixelsize.
Use a low (head) speed setting and a laser power setting of about 1/3 of the maxiumum laser power of the machine.

So for example on a machine with a maximum laser power setting of 1000 and a laser beam width of 0.08:
```
# generate test images 200 by 200 pixels wide and write them to the file system
> image2gcode --genimages 200 200 1
# greate gcode
> image2gcode --showimage --validate --speed 800 --maxpower 300 --pixelsize 0.16 raster_1_pixel_horizontal_200x200_pixels.png r1ph200p.gc
> image2gcode --showimage --validate --speed 800 --maxpower 300 --pixelsize 0.16 squarefilled_200x200_pixels.png sf200p.gc
# run r1ph200p.gc sf200p.gc on the laser machine (use commandline program 'grblhud' for example)
```
One strategy is to start at twice the minimum pixel size and make it smaller until the pixels 'fuse'.

**White balance**

When the pixelsize is determined - say 0.1mm - calibrate the white balance by varying head speed and maximum laser power, using this pixelsize.
Use calibration files ```gradient_diagonal``` and ```gradient_banding``` for that:
```
> image2gcode --showimage --validate --speed 800 --maxpower 300 --pixelsize 0.1 gradient_diagonal_200x200_pixels.png gd200p.gc
> image2gcode --showimage --validate --speed 800 --maxpower 300 --pixelsize 0.1 gradient_banding_200x200_pixels.png gb200p.gc
```
Dark and white has to be in balance as shown by the images on your screen. When the balance is shifted to black (for example) increase *speed* or lower *maxpower*.
But note that calibration images have a pixel value in range of 0 to 256 (*image2gcode* converts all images to 8 bits per pixel), so ideally to have the same dynamic range
use a *maxpower* setting of 256 or more (*maxpower* of more than 256 increase the dynamic range, but at the loss of a smooth gradient).

One strategy is to start at a low speed setting, if the image is mostly black, use less power untill you see at least some 'banding' or a bit of gray.
From this setting increase speed untill the white balance is perfect.
Note that too much speed will make the pixels less defined, meaning they smear out and the image will have less contrast and will lose its sharpness.

**Cutting depth**

A more powerful laser - say 10W instead of 5W per 0.1mm^2 - will increase the cutting depth, but not nesessarly the blackness of a pixel.
So images engraved by a powerfull laser will have more relief which makes it visible at a wider angle. 
I found that calibrating a more powerfull laser did not give it a better white balance, and did not increase speed as much as I expected.
The ideal white balance for my 5W laser is at *speed* 1200 and *maxpower* 300, while the 10W laser optimum is a *speed* of 1400 and *maxpower* of 300.

Cutting depth of the 10W laser seems to be a factor 2 though.
Also, contrast of the 5W laser is a lot better than that of the 10W laser. Images engraved by the 5W laser are laser sharp and smooth, while the 10W laser images are sharp, have reasonable smoothness and twice the cutting depth.

**Wood**

Obviously wood hardness determines the cutting depth (relief) of the engraving and a dark color reduces the contrast of the image.
Note also that the white balance of an engraving is possibly shifted for different types of wood.

