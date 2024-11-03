# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2024
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    'name': "Advance Filter Management",
    'version': "14.0.1.1.2",
    'summary': "A custom filter management model helps you filter your data according to your needs, You can create a custom filter using the domain, It's easy to configure, You can filter records as per environment user, You can filter records as per the environment comapny, It will help you to filter your data with time duration, This modul provide group by filter too, You can select any stored field in the group by filter, Categorizes records based on user-defined domain conditions, Allows creation of personalized filters with adjustable values, Filters data based on specified domain conditions.",
    'description':"""
        A custom filter management model helps you filter your data according to your needs.
        You can create a custom filter using the domain.
        It's easy to configure.
        You can filter records as per environment user.
        You can filter records as per the environment comapny.
        It will help you to filter your data with time duration.
        This modul provide group by filter too.
        You can select any stored field in the group by filter.
        Categorizes records based on user-defined domain conditions.
        Allows creation of personalized filters with adjustable values.
        Filters data based on specified domain conditions.
    """, 
    'author': 'Terabits Technolab',
    'license': 'OPL-1',
    'website': 'https://www.terabits.xyz',
    'depends':['advanced_web_domain_widget'], 
    "price": "100.00",
    "currency": "USD",
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/ir_filters_view.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'application': True,
    'installable': True,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
}
