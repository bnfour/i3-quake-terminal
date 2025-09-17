#!/usr/bin/env python3

# a script for i3 to have one global terminal available on hotkey,
# now with almost proper typing (as in "# type: ignore" interfacing with code outside of standard library)

# requires python3-i3ipc package

# see https://github.com/bnfour/i3-quake-terminal for details,
# MIT license

#region imports

import argparse
import os
import sys
import time

from dataclasses import dataclass
from enum import Enum
from typing import cast, Callable, NoReturn

try:
    import i3ipc
    import psutil
    import Xlib
except ImportError:
    # TODO generalize the error message
    print('i3ipc module not found. Exiting.', file=sys.stderr, flush=True)
    sys.exit(1)

#endregion

version= '2.2->3 indev'

#region definitions

#region definitions -> anchor enums

class HorizontalAlignment(Enum):
    Left = 1
    Centre = 2
    Right = 3

    @staticmethod
    def allowed() -> tuple[str, ...]:
        return ('left', 'l', 'centre', 'center', 'c', 'middle', 'm', 'right', 'r')
    
    @staticmethod
    def from_string(string: str):
        match string.lower()[0]:
            case 'l':
                return HorizontalAlignment.Left
            case 'c' | 'm':
                return HorizontalAlignment.Centre
            case 'r':
                return HorizontalAlignment.Right
            case _:
                raise Exception('Unknown string passed, should never happen.')


class VerticalAlignment(Enum):
    Top = 1
    Centre = 2
    Bottom = 3

    @staticmethod
    def allowed() -> tuple[str, ...]:
        return ('top', 't', 'centre', 'center', 'c', 'middle', 'm', 'bottom', 'b')
    
    @staticmethod
    def from_string(string: str):
        match string.lower()[0]:
            case 't':
                return VerticalAlignment.Top
            case 'c' | 'm':
                return VerticalAlignment.Centre
            case 'b':
                return VerticalAlignment.Bottom
            case _:
                raise Exception('Unknown string passed, should never happen.')

#endregion

#region definitions -> screen/window positioning classes

@dataclass
class Offset(object):
    """Represents distance between two positions on the screen"""
    x: int
    y: int


@dataclass
class Position(object):
    """Represents a position on the screen"""
    x: int
    y: int

    def __add__(self, offset: Offset):
        """Moves a position by a given offset"""
        return Position(self.x + offset.x, self.y + offset.y)


@dataclass
class Size(object):
    """Represents size of an area on the screen"""
    width: int
    height: int


@dataclass
class SizeSettings(object):
    """Represents size setting for the terminal window"""
    # int is assumed absolute pixel value
    # float is assumed multiplier of output's size
    width: int | float
    height: int | float

    def apply_to(self, size: Size) -> Size:
        """Applies settings for the (presumably) output's size, returns result as a new instance for window size"""
        # size is only needed for relative settings
        match self.width:
            case int():
                w = self.width
            case float():
                w = int(self.width * size.width)
        match self.height:
            case int():
                h = self.height
            case float():
                h = int(self.height * size.height)

        return Size(w, h)


@dataclass
class Region(object):
    """Represents an area of the screen: a window, a display, an arbitrary rectangle"""
    position: Position
    size: Size

#endregion

#region definitions -> misc

@dataclass
class Terminal(object):
    """Holds settings for a terminal used in this script"""
    executable: str
    title_command: str


@dataclass
class TypedConfig(object):
    """Holds typed settings for the script for ease of access"""
    size: SizeSettings
    extra_offset: Offset
    horizontal_anchor: HorizontalAlignment
    vertical_anchor: VerticalAlignment
    
    output: str
    window_title: str
    terminal: Terminal
    focus_first: bool

    @staticmethod
    def from_namespace(namespace: argparse.Namespace):
        size = SizeSettings(namespace.width_ratio or namespace.width,
            namespace.height_ratio or namespace.height)
        offset = Offset(namespace.offset_x, namespace.offset_y)
        h_anchor = HorizontalAlignment.from_string(namespace.horizontal)
        v_anchor = VerticalAlignment.from_string(namespace.vertical)
        output = namespace.output
        title = namespace.name
        term = terminals[namespace.terminal]
        focus_first = namespace.focus_first

        return TypedConfig(size, offset, h_anchor, v_anchor, output, title, term, focus_first)

#endregion

#endregion

#region configuration

# TODO consider moving those outside of global scope

# terminal emulators supported by the script
terminals = {
    # generic may work if the terminal does support -T,
    # the proper way is to provide a definition for your favourite terminal emulator
    'generic': Terminal('i3-sensible-terminal', '-T'),
    'urxvt': Terminal('urxvt', '-title'),
}

# default settings for the script
# the values that I use so so I can write less arguments ('-^)b
defaults = TypedConfig(
    SizeSettings(1280, 720),
    Offset(0, 0),
    HorizontalAlignment.Centre,
    VerticalAlignment.Top,
    'main',
    'The terminal',
    terminals['urxvt'],
    False
)

#endregion

#region argparse setup

def get_args() -> tuple[TypedConfig, list[str]]:
    """
    Returns parsed arguments for the script itself,
    and a list of unrecognized arguments to be passed to the terminal emulator as is.
    """
    parser = argparse.ArgumentParser(add_help=False,
                description='A script to have one global terminal window toggleable by a hotkey.',
                epilog='Any unrecognized arguments are passed as is to the terminal emulator. To prevent flickering, please add an i3 rule to move created terminal windows to the scratchpad, for example: for_window [class="URxvt" title="The terminal"] move scratchpad',
                formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    width_group = parser.add_mutually_exclusive_group()
    width_group.add_argument('--width', '-w', type=int, default=defaults.size.width,
        help='set the terminal window width, in pixels')
    width_group.add_argument('--relative-width', '-rw', type=float, dest='width_ratio',
        help='set the terminal window width relative to the output width')

    height_group = parser.add_mutually_exclusive_group()
    height_group.add_argument('--height', '-h', type=int, default=defaults.size.height,
        help='set the terminal window height, in pixels')
    height_group.add_argument('--relative-height', '-rh', type=float, dest='height_ratio',
        help='set the terminal window height relative to the output height')

    # for argparse, these are strings, enum conversion is done in TypedConfig, hence the .name.lower() bit
    parser.add_argument('--horizontal', '-x', choices=HorizontalAlignment.allowed(), default=defaults.horizontal_anchor.name.lower(),
        help='set the terminal window\'s horizontal align')
    parser.add_argument('--vertical', '-y', choices=VerticalAlignment.allowed(), default=defaults.vertical_anchor.name.lower(),
        help='set the terminal window\'s vertical align')

    parser.add_argument('--offset-horizontal', '-oh', '-ox', type=int, dest='offset_x', default=defaults.extra_offset.x,
        help='horizontal offset for the terminal window, in pixels; positive values move to the right')
    parser.add_argument('--offset-vertical', '-ov', '-oy', type=int, dest='offset_y', default=defaults.extra_offset.y,
        help='vertical offset for the terminal window, in pixels; positive values move down')

    parser.add_argument('--focus-first', '-f', dest='focus_first', action="store_true",
        help='if enabled, calling will focus unfocused visible terminal window instead of hiding it; focused terminal will be hidden')

    # TODO (very maybe): implement a 'focused' keyword to open the terminal the output with the currently active workspace,
    # moving it in case it was open somewhere else
    parser.add_argument('--output', '-o', default=defaults.output,
        help='set the terminal window\'s output. Use its name as it appears in xrandr (e.g. DP-2) or main for primary output')
    # user-friendly term names are not stored in defaults itself, so this is awkward
    parser.add_argument('--terminal', '-t', choices=terminals.keys(), default=[k for k, v in terminals.items() if v.executable == defaults.terminal.executable][0],
        help='terminal to use; "generic" calls "i3-sensible-terminal -T NAME", may or may not work depending on terminal')
    parser.add_argument('--name', '-n', default=defaults.window_title,
        help=f'set the terminal window name. Should be unique for the script to work')

    parser.add_argument('--version', '-v', action='version', version=f"bnfour's i3 quake-like terminal {version}")
    parser.add_argument('--help', '-?', action='help', help="show this help message and exit")

    namespace, to_pass = parser.parse_known_args()
    return (TypedConfig.from_namespace(namespace), to_pass)

#endregion

def main(config: TypedConfig, arguments_to_pass: list[str]):
    """
    Main entry point of the script.
    Toggles the visibility of the terminal emulator window if it's present;
    otherwise, creates a new one and shows it.
    """
    i3 = i3ipc.Connection()
    window_tag = generate_window_tag(config.window_title)
    term_by_tag = i3.get_tree().find_marked(window_tag)
    if term_by_tag:
        # TODO we can probably support multiple windows now, though they will be placed on top of each other
        if len(term_by_tag) != 1:
            print(f'Multiple windows tagged "{window_tag}" detected. Please clarify.', file=sys.stderr, flush=True)
            sys.exit(1)

        toggle(term_by_tag[0], i3, config)
    else:
        # an optimization to not iterate through all existing windows,
        # we know the one(s) we're looking for do not exist yet
        existing_window_ids = [w.window for w in i3.get_tree().leaves()] # type: ignore

        pid = os.fork()
        if pid != 0:
            launch_program(config, arguments_to_pass)
        else:
            parent = os.getppid()
            term_by_ppid = find_related_windows(i3, parent, existing_window_ids)
            # TODO we can probably support multiple windows now, though they will be placed on top of each other
            match len(term_by_ppid):
                case 0:
                    print(f'Unable to find a window associated with PID "{parent}" after waiting. Giving up.', file=sys.stderr, flush=True)
                    sys.exit(1)
                case 1:
                    term_by_ppid[0].command(f'mark {window_tag}')
                    show(term_by_ppid[0], i3, config)
                case _:
                    print(f'Multiple windows associated with PID "{parent}" detected. TODO.', file=sys.stderr, flush=True)
                    sys.exit(1)

#region window manipulation code

def toggle(window: i3ipc.Con, i3: i3ipc.Connection, config: TypedConfig):
    """
    Toggles the terminal visibility state.
    Can be configured to focus the visible terminal window first
    before closing on a subsequent call when it's focused.
    """
    if in_scratchpad(window):
        show(window, i3, config)
    else:
        if config.focus_first and not window.focused: # type: ignore
            focus(window)
        else:
            hide(window)

def show(window: i3ipc.Con, i3: i3ipc.Connection, config: TypedConfig):
    """
    Calls internal methods required to calculate the terminal window position
    and size and show it there.
    """
    output_region = get_output_properties(config.output, i3)

    window_size = config.size.apply_to(output_region.size)
    
    # dealing with borders is a bit tricky

    # i3ipc.Con.rect.height is larger than target size
    # and this affect the bottom anchor, so we store the value
    # and compensate for it when needed
    height_diff = cast(int, window.rect.height) - window_size.height # type: ignore
    # we need to take the border width into account when centering horizontally
    border_width = cast(int, window.window_rect.x) # type: ignore

    window_position = get_position(output_region, window_size, config.extra_offset,
        config.horizontal_anchor, config.vertical_anchor, height_diff, border_width)

    window_region = Region(window_position, window_size)

    show_internal(window, window_region)

def show_internal(window: i3ipc.Con, placement: Region):
    """
    Actually moves and resizes the window to dimensions specified.
    Sticky mode is applied only if not already set.
    """
    sticky_command = '' if window.sticky else 'sticky enable, ' # type: ignore
    window.command(f'scratchpad show, {sticky_command}'
        + f'resize set {placement.size.width}px {placement.size.height}px, '
        + f'move position {placement.position.x}px {placement.position.y}px')

def focus(window: i3ipc.Con):
    """Focuses the window"""
    window.command('focus')

def hide(window: i3ipc.Con):
    """Hides the window by moving it to scratchpad"""
    window.command('move scratchpad')

def get_output_properties(name: str, i3: i3ipc.Connection) -> Region:
    """
    Gets screen position and size of a physical output by given name,
    or special 'main' value that specifies the primary output, whatever its actual name is.
    """
    outputs = i3.get_outputs()

    filter_predicate: Callable[[i3ipc.OutputReply], bool] = (lambda x: x.primary) if name == 'main' else (lambda x: x.name == name) # type: ignore
    filtered = tuple(out for out in outputs if filter_predicate(out))

    # surely there is no way two outputs will ever have the same name
    if len(filtered) != 1:
        print(f'Unable to find output "{name}".', file=sys.stderr, flush=True)
        sys.exit(1)
    
    rect = filtered[0].rect # type: ignore

    return Region(Position(rect.x, rect.y), Size(rect.width, rect.height)) # type: ignore

def get_position(output: Region, window_size: Size, window_offset: Offset,
        h_anchor: HorizontalAlignment, v_anchor: VerticalAlignment,
        extra_offset_for_bottom: int, border_width: int) -> Position:
    """Calculates the position for the terminal window per configuration provided"""

    match h_anchor:
        case HorizontalAlignment.Left:
            x = output.position.x
        case HorizontalAlignment.Centre:
            x = output.position.x + (output.size.width - window_size.width) // 2 + border_width
        case HorizontalAlignment.Right:
            x = output.position.x + output.size.width - window_size.width
    
    match v_anchor:
        case VerticalAlignment.Top:
            y = output.position.y
        case VerticalAlignment.Centre:
            y = output.position.y + (output.size.height - window_size.height) // 2
        case VerticalAlignment.Bottom:
            y = output.position.y + output.size.height - window_size.height - extra_offset_for_bottom
    
    return Position(x, y) + window_offset


def in_scratchpad(window: i3ipc.Con) -> bool:
    """Determines whether the provided window is off-screen in scratchpad"""
    return cast(str, window.ipc_data['output']) == '__i3'

def generate_window_tag(name: str) -> str:
    """
    Generates a window tag to use based on provided name.
    Adds _ to the start of the tag, so it is never shown.
    """
    return '_bnqi3_' + name.lower().replace(' ', '_')

#endregion

# TODO consider reusing display?
def match_pids_to_wids(wids: list[int]) -> dict[int, int]:
    """
    For a list of given window ids, queries the display for related process ids,
    returns a dictionary where process ids are mapped to window ids.
    """
    display = Xlib.display.Display()
    ret: dict[int, int] = {}

    for wid in wids:
        specs = [{"client": wid, "mask": Xlib.ext.res.LocalClientPIDMask}] # type: ignore
        r = display.res_query_client_ids(specs)
        for id in r.ids:
            if id.spec.client > 0 and id.spec.mask == Xlib.ext.res.LocalClientPIDMask: # type: ignore
                for value in id.value:
                    ret[value] = wid

    display.close()
    return ret

def launch_program(config: TypedConfig, arguments_to_pass: list[str]) -> NoReturn:
        """
        Launches the configured program with given arguments.
        """
        arguments = [config.terminal.executable, config.terminal.title_command, config.window_title,]
        if arguments_to_pass:
            if (arguments_to_pass[0] == '--'):
                arguments_to_pass = arguments_to_pass[1::]
            arguments.extend(arguments_to_pass)
        try:
            os.execvp(config.terminal.executable, arguments)
        except FileNotFoundError as e:
            print(f'Unable to run "{config.terminal.executable}": {e.strerror}', file=sys.stderr, flush=True)
            sys.exit(1)

def find_related_windows(i3: i3ipc.Connection, pid: int, window_ids_to_skip: list[int]) -> list[i3ipc.Con]:
    """
    Returns a list of windows related to a given pid: the windows may be directly associated with it,
    or has the pid as its (grand*)parent.
    """
    found = []
    # wait for the terminal to appear for about a second
    for _ in range(10):
        time.sleep(0.1)

        windows_to_check = [w for w in i3.get_tree().leaves() if w.window not in window_ids_to_skip] # type: ignore
        data_dict = match_pids_to_wids([w.window for w in windows_to_check]) # type: ignore

        for pid in data_dict.keys():
            if pid == pid:
                found = [w for w in windows_to_check if w.window == data_dict[pid]] # type: ignore
                break
            else:
                if pid in [i.pid for i in psutil.Process(pid).parents()]:
                    found = [w for w in windows_to_check if w.window == data_dict[pid]] # type: ignore
                    break

        if found:
            break
        else:
            # skip the windows we unsuccessfully checked this iteration in the next one
            window_ids_to_skip.extend([w.window for w in windows_to_check]) # type: ignore

    return found

if __name__ == '__main__':
    main(*get_args())
