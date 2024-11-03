# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
import hashlib


def generate_id(text=''):
    m = hashlib.md5()
    m.update(text.encode())
    return str(int(m.hexdigest(), 16))[0:12]
