# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from base64 import b64encode

import requests


def get_mp_asset(url):
    try:
        response = requests.get(url)
        return b64encode(response.content).decode()
    except:
        return None
