# -*- coding: utf-8 -*-

from .awesome_dark_style1 import dark_style1
from .awesome_dark_style2 import dark_style2
from .awesome_dark_style3 import dark_style3
from .awesome_dark_style4 import dark_style4
from .awesome_dark_vars import default_vars

dark_mode = {
    "name": "dark",
    "default_vars": default_vars,
    "theme_styles": [
        dark_style1,
        dark_style2,
        dark_style3,
        dark_style4
    ]
}
