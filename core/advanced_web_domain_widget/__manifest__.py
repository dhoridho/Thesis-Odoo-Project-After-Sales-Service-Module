# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2021-22
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    'name': 'Advanced Web Domain Widget',
    'version': '14.0.3.0.0',
    'summary': 'Set all relational fields domain by selecting its records unsing `in, not in` operator.',
    'sequence': 1,
    'author': 'Terabits Technolab',
    'license': 'OPL-1',
    'website': 'https://www.terabits.xyz',
    'description':"""
      
        """,
    "price": "29.00",
    "currency": "USD",
    'depends':['base','web'],
    'data':[
        'views/assets.xml',
    ],
    'qweb': [
        'static/src/xml/domain_base.xml'
    ],
'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
