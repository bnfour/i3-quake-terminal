# i3-quake-terminal
A companion script for [i3 window manager](https://i3wm.org/) to have a global drop-down terminal window toggleable by a hotkey.

# Installation
Just drop `quake-terminal.py` somewhere and [create a keybind](#hotkey) to launch it in your i3 config.

## Requirements
Requires `i3ipc` package ([PyPI](https://pypi.org/project/i3ipc/), [GitHub](https://github.com/altdesktop/i3ipc-python)).

Fellow Fedora enjoyers:  
`sudo dnf install python3-i3ipc`

For other distros, consult your package manager repos, or install via `pip`:  
`python -m pip install i3ipc`

# Usage
The script creates a single sticky terminal window on specified output, toggleable via calling the script again. The first call will show the window, the second call will hide it, and so on. If the window is closed, the first subsequent call will create and show a new one.

This script can be used to provide a quickly accessible general terminal window, or a `htop` instance as a task manager. Feel free to invent your own uses!

## i3 configuration
This script requires some configuration on i3's side to work properly. See [docs](https://i3wm.org/docs/userguide.html#configuring) for details.

### Hotkey
Minimal configuration is to [add a keybind](https://i3wm.org/docs/userguide.html#keybindings) to launch the script.

Here's an example setting <kbd>Mod</kbd>+<kbd>\`</kbd> release to launch the script with its [default settings](#default-settings):
```
bindsym $mod+grave --release exec --no-startup-id /path/to/quake-terminal.py
```

### Flickering
To prevent terminal window first appearing in default position first and visibly teleporting to proper position, add a [`for_window` rule](https://i3wm.org/docs/userguide.html#for_window) to the config to move it to the scratchpad by default.

An example for default settings, an `urxvt` window called "The terminal":
```
for_window [class="URxvt" title="The terminal"] move scratchpad
```
Adjust class and/or title as needed. Class name for your terminal emulator can be found using `xprop`.

## Configuration
The script accepts a set options to control the terminal window's properties and behaviour. There are reasonable default values, so the script will work out of the box without any arguments (assuming you use `rxvt-unicode`).

## Available settings
Output of built-in help command:

```
$ quake-terminal.py -?
usage: quake-terminal.py [--width WIDTH | --relative-width WIDTH_RATIO] [--height HEIGHT | --relative-height HEIGHT_RATIO] [--horizontal {left,l,centre,center,c,middle,m,right,r}] [--vertical {top,t,centre,center,c,middle,m,bottom,b}] [--offset-horizontal OFFSET_X] [--offset-vertical OFFSET_Y] [--focus-first] [--output OUTPUT] [--terminal {generic,urxvt}]
                         [--name NAME] [--version] [--help]

A script to have one global terminal window toggleable by a hotkey.

options:
  --width, -w WIDTH     set the terminal window width, in pixels (default: 1280)
  --relative-width, -rw WIDTH_RATIO
                        set the terminal window width relative to the output width (default: None)
  --height, -h HEIGHT   set the terminal window height, in pixels (default: 720)
  --relative-height, -rh HEIGHT_RATIO
                        set the terminal window height relative to the output height (default: None)
  --horizontal, -x {left,l,centre,center,c,middle,m,right,r}
                        set the terminal window's horizontal align (default: centre)
  --vertical, -y {top,t,centre,center,c,middle,m,bottom,b}
                        set the terminal window's vertical align (default: top)
  --offset-horizontal, -oh, -ox OFFSET_X
                        horizontal offset for the terminal window, in pixels; positive values move to the right (default: 0)
  --offset-vertical, -ov, -oy OFFSET_Y
                        vertical offset for the terminal window, in pixels; positive values move down (default: 0)
  --focus-first, -f     if enabled, calling will focus unfocused visible terminal window instead of hiding it; focused terminal will be hidden (default: False)
  --output, -o OUTPUT   set the terminal window's output. Use its name as it appears in xrandr (e.g. DP-2) or main for primary output (default: main)
  --terminal, -t {generic,urxvt}
                        terminal to use; "generic" calls "i3-sensible-terminal -T NAME", may or may not work depending on terminal (default: urxvt)
  --name, -n NAME       set the terminal window name. Should be unique for the script to work (default: The terminal)
  --version, -v         show program's version number and exit
  --help, -?            show this help message and exit

Any unrecognized arguments are passed as is to the terminal emulator. To prevent flickering, please add an i3 rule to move created terminal windows to the scratchpad, for example: for_window [class="URxvt" title="The terminal"] move scratchpad
```

>[!NOTE]
>`-h` is used as a shorthand for `--height`, so the short version of `--help` is `-?`.

### Window sizing
<!-- TODO one absolute and one relative do not work lule -->
The window size can be set either as an absolute pixel value or as a multiplier of output's size.

`-w 960 -h 540` is equivalent to `-rw 0.5 -rh 0.5` for a 1920×1080 output. Absolute and relative sizes can be mixed, so `-w 960 -rh 0.5` (or vice versa) will also work.

### Window positioning
The window is anchored relatively to one of nine anchors of a display output, with an optional offset.

#### Output
To select an output to use, use its name (as reported by `xrandr --listmonitors`, e.g. "DP-0") with `--output`. Special "main" value is also accepted to use the output set as primary, regardless of its name.

#### Anchoring
The nine anchors are all possible combinations of three vertical (top, middle, bottom) and horizontal (left, middle, bottom) anchors:

| -v ╲ -h | left | middle | right |
| ---: | :--- | :---: | ---: |
| top | ![](readme-images/tl.jpg) | ![](readme-images/tm.jpg) | ![](readme-images/tr.jpg) |
| middle | ![](readme-images/ml.jpg) | ![](readme-images/mm.jpg) | ![](readme-images/mr.jpg) |
| bottom | ![](readme-images/bl.jpg) | ![](readme-images/bm.jpg) | ![BR pepeLaugh](readme-images/br.jpg) |

#### Offset
The window can be offset from the anchored position by a set amount of pixels on both axes. Positive X moves to the right, positive Y moves down:

| -oy ╲ -ox | -150 | 0 | 150 |
| ---: | :---: | :---: | :---: |
| -150 | ![](readme-images/offset-tl.jpg) | ![](readme-images/offset-tm.jpg) | ![↗️ LULE](readme-images/offset-tr.jpg) |
| 0 | ![](readme-images/offset-ml.jpg) | ![](readme-images/offset-mm.jpg) | ![](readme-images/offset-mr.jpg) |
| 150 | ![](readme-images/offset-bl.jpg) | ![](readme-images/offset-bm.jpg) | ![](readme-images/offset-br.jpg) |

Green grid is 1280×720 centered. The actual window is slightly bigger because of its header.

### Other script options
(Not related to window's size or position.)

#### Focus behaviour
By default, invoking the script when the associated window is visible on the screen will hide it regardless of its status. With `--focus-first` set, the window will be focused if it had no focus, and another subsequent invocation will hide it (assuming the focus did not move).

#### Window title
`--name` sets the title for the terminal emulator's window. It needs to be unique for the script to properly initialize. After script initialization (the window was shown for the first time), the title can be changed freely.

#### Terminal
`--terminal` sets the terminal emulator app to call.

This script only really supports [`urxvt`](https://software.schmorp.de/pkg/rxvt-unicode.html) out of the box (as it's _the_ terminal emulator I use). "generic" option might work for other terminal emulators if:
- `i3-sensible-terminal` launches your terminal emulator
- your terminal emulator supports `-T` as an argument to set window title

<!-- TODO don't forget to update the line number on future updates -->
Otherwise, the script should be extended to work with another terminal emulator. To add an entry for another terminal emulator, add an entry to the [`terminals` dict](https://github.com/bnfour/i3-quake-terminal/blob/main/quake-terminal.py#L175):
```python
terminals = {
    # ...
    # original for comparison
    'urxvt': Terminal('urxvt', '-title'),
    # add your own favourite terminal emulator
    'user-friendly-name': Terminal('executable-name', 'arg-to-set-title')
}
```

- `user-friendly-name` is used to set the terminal emulator name in script arguments; can be set to whatever
- `executable-name` is the actual executable name
- `arg-to-set-title` is the argument to set the title, with all leading dashes, if needed

The parameters will be used to call the terminal emulator like this:
```bash
executable-name arg-to-set-title "Actual title set by another argument"
```

### Argument passing
The script passes any arguments it did not recognize as its own to the terminal emulator as is.

### Default settings
With the default settings, the script will create a 1280×720px `urxvt` window named "The terminal" in the top middle of the main output. By default, if the window if visible (regardless of its focus status) it will be hidden on the second execution of the script.

# Credits
This script is inspired by https://github.com/NearHuscarl/i3-quake. If this script is not exactly what you're looking for, check it out as well!

# License
MIT
