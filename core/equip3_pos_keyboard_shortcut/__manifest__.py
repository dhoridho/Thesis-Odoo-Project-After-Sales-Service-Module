# -*- coding: utf-8 -*-
{
    'name': "Equip3 - POS Keyboard Shortcut",
    'version': '1.1.2',
    'author': "Hashmicro",
    'depends': ['equip3_pos_general'],
    'summary': """
        Manage POS Shortcut""",

    "description":  """POS Keyboard Shortcuts
        POS Hotkeys
        Shortcut Keys
        POS Shortcut Keys
        POS Keys
        POS Session Shortcuts
        Hotkeys Shortcuts
        Shortcut keys POS
        Shortcut POS Keys
        Assign Shortcuts Keys
        Assign Keyboard Keys
        Odoo POS Keyboard Shortcuts
        Shortcuts
        POS Shortcuts
        POS Shortcut keys""",
    'category': 'Uncategorized',
    "data":  [
        'security/ir.model.access.csv',
        'views/pos_keyboard_shortcuts_view.xml',
        'views/pos_config_view.xml',
        'views/assets.xml',
    ],
   "qweb":  ['static/src/xml/pos.xml'],
   "pre_init_hook":  "pre_init_check",
   'application': False,
   'auto_install': False,
   'installable': True,
}
