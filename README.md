# i3-quake-terminal
A script for i3 window manager to have a global drop-down terminal window toggleable by a hotkey.

# Installation
Just drop `quake-terminal.py` somewhere and [create a keybind](#setting-the-hotkey) to launch it in your i3 config.

## Requirements
Requires `i3ipc` package ([PyPI](https://pypi.org/project/i3ipc/), [GitHub](https://github.com/altdesktop/i3ipc-python)).

Fellow Fedora enjoyers:  
`sudo dnf install python3-i3ipc`

For other distros, consult your package manager repos, or install via `pip`:  
`python -m pip install i3ipc`

# Usage
The script creates a single sticky terminal window on specified output, toggleable via calling the script again. The first call will show the window, the second call will hide it, and so on. If the window is closed, the first subsequent call will create and show a new one.

This script can be used to provide a quickly accessible general terminal window, or a `htop` instance as a task manager. Feel free to invent your own uses!

## Setting the hotkey
Minimal configuration on i3 side is to add a keybind to launch the script.

Here's an example setting <kbd>Mod</kbd>+<kbd>\`</kbd> release to launch the script with its [default settings](#default-settings):
```
bindsym $mod+grave --release exec --no-startup-id /path/to/quake-terminal.py
```

## Available settings
The script accepts many options to set the terminal window's properties and behaviour:

```
$ quake-terminal.py -?
usage: quake-terminal.py [--width WIDTH | --relative-width WIDTH_RATIO] [--height HEIGHT | --relative-height HEIGHT_RATIO] [--horizontal {left,l,centre,center,c,right,r}] [--vertical {top,t,centre,center,c,bottom,b}] [--offset-horizontal OFFSET_X] [--offset-vertical OFFSET_Y] [--focus-first] [--output OUTPUT] [--terminal {generic,urxvt}] [--name NAME] [--version] [--help]

A script to have one global terminal window toggleable by a hotkey.

options:
  --width WIDTH, -w WIDTH
                        set the terminal window width, in pixels (default: 1280)
  --relative-width WIDTH_RATIO, -rw WIDTH_RATIO
                        set the terminal window width relative to the output width (default: None)
  --height HEIGHT, -h HEIGHT
                        set the terminal window height, in pixels (default: 720)
  --relative-height HEIGHT_RATIO, -rh HEIGHT_RATIO
                        set the terminal window height relative to the output height (default: None)
  --horizontal {left,l,centre,center,c,right,r}, -x {left,l,centre,center,c,right,r}
                        set the terminal window's horizontal align (default: centre)
  --vertical {top,t,centre,center,c,bottom,b}, -y {top,t,centre,center,c,bottom,b}
                        set the terminal window's vertical align (default: top)
  --offset-horizontal OFFSET_X, -oh OFFSET_X, -ox OFFSET_X
                        horizontal offset for the terminal window, in pixels; positive values move to the right (default: 0)
  --offset-vertical OFFSET_Y, -ov OFFSET_Y, -oy OFFSET_Y
                        vertical offset for the terminal window, in pixels; positive values move down (default: 0)
  --focus-first, -f     if enabled, calling will focus unfocused visible terminal window instead of hiding it; focused terminal will be hidden (default: False)
  --output OUTPUT, -o OUTPUT
                        set the terminal window's output. Use its name as it appears in xrandr (e.g. DP-2) or main for primary output (default: main)
  --terminal {generic,urxvt}, -t {generic,urxvt}
                        terminal to use; "generic" calls "i3-sensible-terminal -T NAME", may or may not work depending on terminal (default: urxvt)
  --name NAME, -n NAME  set the terminal window name. Should be unique for the script to work (default: The terminal)
  --version, -v         show program's version number and exit
  --help, -?            show this help message and exit

Any unrecognized arguments are passed as is to the terminal emulator. To prevent flickering, please add an i3 rule to move created terminal windows to the scratchpad, for example: for_window [class="URxvt" title="The terminal"] move scratchpad
```

### Argument passing
The script passes any provided arguments it did not recognize as its own to the terminal emulator as is.

### Default settings
With the default settings, the script will create a 1280×720px `urxvt` window named "The terminal" in the top middle of the main output. By default, if the window if visible (regardless of its focus status) it will be hidden on the second execution of the script.

## Terminal emulator configuration
This script only really supports `urxvt` out of the box (as it's _the_ terminal emulator I use). "generic" option might work for other terminal emulators if:
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

## Flickering
To prevent terminal window first appearing in default position first and visibly teleporting to proper position, add a [`for_window` rule](https://i3wm.org/docs/userguide.html#for_window) to your i3 config to move it to the scratchpad by default.

An example for default settings, an `urxvt` window called "The terminal":
```
for_window [class="URxvt" title="The terminal"] move scratchpad
```
Adjust class and title as needed. Class name for your terminal emulator can be found using `xprop`.

# Credits
This script is inspired by https://github.com/NearHuscarl/i3-quake. If this script is not exactly what you're looking for, check it out as well!

# License
MIT
