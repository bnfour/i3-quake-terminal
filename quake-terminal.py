#!/usr/bin/env python3

# a script for i3 to have one global terminal available on hotkey
# requires python3-i3ipc package

# see https://github.com/bnfour/i3-quake-terminal for details

#region imports

import argparse
import os
import sys
import time

try:
    import i3ipc
except ImportError:
    print('i3ipc module not found. Exiting.')
    sys.exit(1)

from typing import NamedTuple, Final

#endregion

#region configuration

version: Final = "2.0"

class Defaults(object):
    """
    Holds default settings for the script.
    The default values is the one I use, so I can provide less arguments on launch ('-^)b
    """
    width: Final = 1280
    height: Final = 720
    output: Final = 'main'
    horizontal: Final = 'centre'
    vertical: Final = 'top'
    name: Final = 'The terminal'
    terminal: Final = 'urxvt'
    offset_x: Final = 0
    offset_y: Final = 0
    # --focus-first being false by default is implied by its argument definition
    # relative width and height is not set by default

class Allowed(object):
    """Holds list of values accepted by some of the options"""
    horizontal: Final = ('left', 'l', 'centre', 'c', 'right', 'r')
    vertical: Final = ('top', 't', 'centre', 'c', 'bottom', 'b')

class Terminal(NamedTuple):
    """Holds settings for a terminal used in this script"""
    executable: str
    title_command: str

terminals: Final = {
    # generic may work if the terminal does support -T,
    # the proper way is to provide a definition for your favourite terminal emulator
    'generic': Terminal('i3-sensible-terminal', '-T'),
    'urxvt': Terminal('urxvt', '-title'),
}

def get_args() -> tuple[argparse.Namespace, list[str]]:

    parser = argparse.ArgumentParser(add_help=False,
                description='A script to have one global terminal window toggleable by a hotkey.',
                epilog='Any unrecognized arguments are passed as is to the terminal emulator. To prevent flickering, please add an i3 rule to move created terminal windows to the scratchpad, for example: for_window [class="URxvt" title="The terminal"] move scratchpad',
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    width_group = parser.add_mutually_exclusive_group()
    width_group.add_argument('--width', '-w', type=int, default=Defaults.width,
        help='set the terminal window width, in pixels')
    width_group.add_argument('--relative-width', '-rw', type=float, dest='width_ratio',
        help='set the terminal window width relative to the output width')

    height_group = parser.add_mutually_exclusive_group()
    height_group.add_argument('--height', '-h', type=int, default=Defaults.height,
        help='set the terminal window height, in pixels')
    height_group.add_argument('--relative-height', '-rh', type=float, dest='height_ratio',
        help='set the terminal window height relative to the output height')

    parser.add_argument('--horizontal', '-x', choices=Allowed.horizontal, default=Defaults.horizontal,
        help='set the terminal window\'s horizontal align')
    parser.add_argument('--vertical', '-y', choices=Allowed.vertical, default=Defaults.vertical,
        help='set the terminal window\'s vertical align')

    parser.add_argument('--offset-horizontal', '-oh', '-ox', type=int, dest='offset_x', default=Defaults.offset_x,
        help='horizontal offset for the terminal window, in pixels; positive values move to the right')
    parser.add_argument('--offset-vertical', '-ov', '-oy', type=int, dest='offset_y', default=Defaults.offset_y,
        help='vertical offset for the terminal window, in pixels; positive values move down')

    parser.add_argument('--focus-first', '-f', dest='focus_first', action="store_true",
        help='if enabled, calling will focus unfocused visible terminal window instead of hiding it; focused terminal will be hidden')

    # TODO (very maybe): implement a 'focused' keyword to open the terminal the output with the currently active workspace,
    # moving it in case it was open somewhere else
    parser.add_argument('--output', '-o', default=Defaults.output,
        help='set the terminal window\'s output. Use its name as it appears in xrandr (e.g. DP-2) or main for primary output')
    parser.add_argument('--terminal', '-t', choices=terminals.keys(), default=Defaults.terminal,
        help='terminal to use; "generic" calls "i3-sensible-terminal -T NAME", may or may not work depending on terminal')
    parser.add_argument('--name', '-n', default=Defaults.name,
        help=f'set the terminal window name. Should be unique for the script to work')

    parser.add_argument('--version', '-v', action='version', version=f"bnfour's i3 quake-like terminal {version}")
    parser.add_argument('--help', '-?', action='help', help="show this help message and exit")

    return parser.parse_known_args()

#endregion

def main(config: argparse.Namespace, arguments_to_pass: list[str]):

    i3 = i3ipc.Connection()
    window_tag = generate_window_tag(config.name)

    term_by_tag = i3.get_tree().find_marked(window_tag)
    if term_by_tag:
        if len(term_by_tag) != 1:
            print(f'Multiple windows tagged "{window_tag}" detected. Please clarify.')
            sys.exit(1)

        toggle(term_by_tag[0], i3, config)
    else:
        pid = os.fork()
        if pid != 0:
            name, title_command = terminals[config.terminal]
            arguments = [name, title_command, config.name,]
            if arguments_to_pass:
                arguments.extend(arguments_to_pass)
            try:
                os.execvp(name, arguments)
            except FileNotFoundError as e:
                print(f'Unable to run "{name}": {e.strerror}')
                sys.exit(1)
        else:
            term_by_name = None
            # wait for the terminal to appear for a second
            for i in range(10):
                time.sleep(0.1)
                term_by_name = i3.get_tree().find_titled(config.name)
                if term_by_name:
                    break
            else:
                print(f'Unable to find a window with title "{config.name}" after waiting. Giving up.')
                sys.exit(1)

            if len(term_by_name) != 1:
                print(f'Multiple windows with title "{config.name}" detected. Please use --name to set an unique one.')
                sys.exit(1)

            term_by_name[0].command(f'mark {window_tag}')
            show(term_by_name[0], i3, config)

def toggle(window: i3ipc.Con, i3: i3ipc.Connection, config: argparse.Namespace):
    """
    Toggles the terminal state, shows or hides it.
    Can be configured to focus the terminal window first before closing on
    a subsequent call.
    """
    if in_scratchpad(window):
        show(window, i3, config)
    else:
        if not window.focused and config.focus_first:
            focus(window)
        else:
            hide(window)

def show(window: i3ipc.Con, i3: i3ipc.Connection, config: argparse.Namespace):
    """
    Calls internal methods required to calculate the terminal window position
    and size and show it there
    """
    output_position, output_size = get_output_properties(config.output, i3)
    output_width, output_height = output_size
    # if relative ratio is set, it overrides size in pixels
    width = int(config.width_ratio * output_width) if config.width_ratio else config.width
    height = int(config.height_ratio * output_height) if config.height_ratio else config.height

    window_size = (width, height)
    window_offset = (config.offset_x, config.offset_y)
    
    window_position = get_position(output_position, output_size, window_size,
        window_offset, config.horizontal, config.vertical)

    show_internal(window, window_position, window_size)

def show_internal(window: i3ipc.Con, position: tuple[int, int], size: tuple[int, int]):
    """Actually moves and resizes the window to dimensions specified"""
    x, y = position
    w, h = size
    window.command('scratchpad show, sticky enable,'
        + f' resize set {w}px {h}px, move position {x}px {y}px')

def focus(window: i3ipc.Con):
    """Focuses the window"""
    window.command('focus')

def hide(window: i3ipc.Con):
    """Hides the window by moving it to scratchpad"""
    window.command('move scratchpad')

def get_output_properties(name: str, i3: i3ipc.Connection) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Gets dimensions of a physical output by given name, or special 'main' value
    that specifies the primary output, whatever its name is.
    Returns output's dimesions as ((x position, y position), (width, height))
    """
    outputs = i3.get_outputs()

    if name == 'main':
        filtered = tuple(out for out in outputs if out.primary)
    else:
        filtered = tuple(out for out in outputs if out.name == name)
    # surely there is no way two outputs will ever have the same name
    if len(filtered) != 1:
        print(f'Unable to find output "{name}".')
        sys.exit(1)
    
    rect = filtered[0].rect
    return ((rect.x, rect.y), (rect.width, rect.height))

def get_position(output_origin: tuple[int, int], output_size: tuple[int, int],
        window_size: tuple[int, int], window_offset: tuple[int, int],
        h_anchor: str, v_anchor: str) -> tuple[int, int]:
    """Calculates the position for the terminal window per configuration provided"""
    x0, y0 = output_origin
    w0, h0 = output_size
    w, h = window_size
    ox, oy = window_offset

    if h_anchor.startswith('l'):
        x = x0
    elif h_anchor.startswith('c'):
        x = x0 + (w0 - w) // 2
    elif h_anchor.startswith('r'):
        x = x0 + w0 - w

    if v_anchor.startswith('t'):
        y = y0
    elif v_anchor.startswith('c'):
        y = y0 + (h0 - h) // 2
    elif v_anchor.startswith('b'):
        y = y0 + h0 - h

    return (x + ox, y + oy)

def in_scratchpad(window: i3ipc.Con) -> bool:
    """Determines whether the provided window is off-screen in scratchpad"""
    return window.ipc_data['output'] == '__i3'

def generate_window_tag(name: str) -> str:
    """
    Generates a window tag to use based on provided name.
    Adds _ to the start of the tag, so it is never shown.
    """
    return '_bnqi3_' + name.lower().replace(' ', '_')


if __name__ == '__main__':
    main(*get_args())
