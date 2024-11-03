# -*- coding: utf-8 -*-

from .awesome_blue_style1 import blue_style1
from .awesome_blue_style2 import blue_style2
from .awesome_blue_style3 import blue_style3
from .awesome_blue_style4 import blue_style4
from .awesome_blue_vars import default_vars

blue_mode = {
    "name": "blue",
    "default_vars": default_vars,
    "theme_styles": [
        blue_style1,
        blue_style2,
        blue_style3,
        blue_style4
    ]
}


