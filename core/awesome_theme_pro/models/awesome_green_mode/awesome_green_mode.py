# -*- coding: utf-8 -*-

from .awesome_green_style1 import green_style1
from .awesome_green_style2 import green_style2
from .awesome_green_style3 import green_style3
from .awesome_green_style4 import green_style4
from .awesome_green_vars import default_vars

green_mode = {
    "name": "green",
    "default_vars": default_vars,
    "theme_styles": [
        green_style1,
        green_style2,
        green_style3,
        green_style4
    ]
}
