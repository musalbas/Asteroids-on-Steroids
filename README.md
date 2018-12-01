Asteroids on Steroids
=====================

Destroy your desktop by turning it into a game of Asteroids...

`./aos.py --screen`

<img src="https://musalbas.com/blog/img/Asteroids-on-Steroids/gameplay_shot_1.png"/>

...or the president's face (or any other image that you specify).

`./aos.py obama.jpg`

<img src="https://musalbas.com/blog/img/Asteroids-on-Steroids/gameplay_shot_2.png"/>

Asteroids on Steroids is a variation of the classic 'Asteroids' arcade game, with a unique twist. Instead of destroying space asteroids, you can destroy automatically-identified elements of any image you specify.

Asteroids on Steroids automatically identifies the different elements of the image without any user input, by comparing the different colours in different regions of the image. Regions of the image that are connected by the same colour are considered to be one 'asteroid'. It's the equivalence of the 'magic wand' tool in Photoshop or the 'fuzzy selection' tool in GIMP.

Modes
-----

<small>(Important: The left and right mouse buttons do different things in game mode.</small>

* <small>Use the left mouse button to destroy existing asteroids.</small>
* <small>Use the right mouse button to create new asteroids based on the clicked area. NOTE: if the initial new asteroids are too small in width or height, they will not be created.)</small>

**Normal game mode**

`"./aos.py image-path"` where image-path is the path of an image

Destroy any image of your choice.

**Desktop game mode**

`"./aos.py --screen"`

Destroy your current screen.

**Prank mode**

`"./aos.py --prankMode"`

Prank your friends by discretely running this mode while they're not paying attention to their computer. When they start clicking on their screen, they will involuntarily destroy their own desktop. The only way to exit prank mode is by typing 'stopit'.

**Screensaver mode**

`"./aos.py image-path --screensaverMode"` for an image

`"./aos.py --screen --screensaverMode"` for your current screen

The game will randomly create and destroy asteroids based on an image of your choice, or your current screen.

See `"./aos.py -h"` for a full list of arguments. (There are probably too many.)

Controls
--------

**WASD/arrow keys**

Move your ship, relative to the current position of your mouse cursor.

**LEFT click**

Destroy existing asteroids.

**RIGHT click**

Create a new asteroid based on the region of the image you right click.

**C key/SHIFT key**

Launch the mega bullet. (25 bullets at the same time, at a tripled maximum range.)

**P key**

Pause/unpause game.

**T key**

Toggle show game statistics.

**F key**

Toggle show FPS rate.

**H key**

Save screenshot of game to screenshot.png.

**ESC key**

Exit game.

Element/asteroid identification
-------------------------------

The effectiveness of element identification can vary depending on the contrast of the image used. Try the following flags to adjust the magic wand/flood fill tool:

**`-sct/--sameColourTolerance` (0-255) (default: 10)**

The maximum difference in RGB values that are considered to be the same colour. Decreasing the SCT will cause elements to be smaller. For photographs, try a value of around 3 or 4.

**`-cp/--colourPalette` (0-16581375) (default: unchanged)**

The number of colours that the underlay image (used to identify elements) will be reduced to. Values below 255 are sensible. Decreasing the CP will cause elements of the same colour more likely to be grouped together, and vice versa for elements of different colours. This should be used for high-contrast images that use a few, but very different colours.

**`-pc/--pixelConnectivity` (4 or 8) (default: 4)**

The number of neighbouring pixels to check when looking for pixels of the same colour. A pixel connectivity value of 8 will cause elements to be bigger.
