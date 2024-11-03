# -*- coding: utf-8 -*-
{
    "name": "Multi-selection for one2many fields",
    "version": "1.1.1",
    "author": "Riddhi Patel",
    "summary": "This widget adds the capability for selecting multiple records in one2many fields"
               " and work on those records",
    "category": "Web",
    "depends": ['web'],
    "data": [
        "view/web_assets.xml",
    ],
    "qweb":[
        'static/src/xml/widget_view.xml',
    ],
    "auto_install": False,
    "installable": True,
    'license': 'AGPL-3',
    "application": False,
}