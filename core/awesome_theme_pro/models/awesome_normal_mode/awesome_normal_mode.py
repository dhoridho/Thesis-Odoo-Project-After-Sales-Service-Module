# -*- coding: utf-8 -*-

from .awesome_normal_style1 import normal_style1
from .awesome_normal_style2 import normal_style2
from .awesome_normal_style3 import normal_style3
from .awesome_normal_style4 import normal_style4

normal_mode = {
    "name": "normal",
    "default_vars": {},
    "theme_styles": [
        normal_style1,
        normal_style2,
        normal_style3,
        normal_style4,
    ]
}
