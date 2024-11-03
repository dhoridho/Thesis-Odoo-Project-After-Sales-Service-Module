# -*- coding: utf-8 -*-
{
    'name': "Equip3 - General Attachment",
    'version': '1.1.2',
    'author': "Hashmicro",
    'depends': ['web','base','equip3_hashmicro_ui'],
    'summary': """
        Add feature action menu attachment for all form view""",

    'description': """
    Add feature action menu attachment for all form view
        
    """,
    'category': 'Uncategorized',
    'data': [
        'views/assets.xml',

   ],
   'qweb': [
            'static/src/xml/*.xml',
   ],
   'application': False,
   'auto_install': True,
   'installable': True,
}