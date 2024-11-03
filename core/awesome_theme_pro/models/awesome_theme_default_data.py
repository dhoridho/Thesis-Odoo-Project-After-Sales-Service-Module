# -*- coding: utf-8 -*-

from .awesome_normal_mode.awesome_normal_mode import normal_mode
from .awesome_dark_mode.awesome_dark_mode import dark_mode
from .awesome_blue_mode.awesome_blue_mode import blue_mode
from .awesome_green_mode.awesome_green_mode import green_mode

version = "14.0.0.3"

default_modes = {
    "normal": normal_mode,
    "dark": dark_mode,
    "blue": blue_mode,
    "green": green_mode
}
