# -*- coding: utf-8 -*-
{
    'name': "Equip3 - POS Indo Numpad",
    'version': '1.1.1',
    'author': "Hashmicro",
    'depends': ['equip3_pos_general'],
    'summary': """
        Manage POS Indo Numpad""",

    "description":  """Manage POS Indo Numpad""",
    'category': 'Uncategorized',
    "data":  [
        'views/assets.xml',
    ],
   "qweb":  ['static/src/xml/Screens/PaymentScreen/*.xml'],
   'application': False,
   'auto_install': False,
   'installable': True,
}
