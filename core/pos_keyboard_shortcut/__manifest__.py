# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
    "name":  "POS Keyboard Shortcuts",
    "summary":  """Odoo POS Keyboard Shortcuts module allows to use Shortcuts for your Odoo POS. You can define various hotkeys on your keyboards to create shortcuts.Shortcut|Keyboard ShortCuts|Hotkeys|Custom Keyboard ShortCuts""",
    "category":  "Point of Sale",
    "version":  "1.1.1",
    "author":  "Webkul Software Pvt. Ltd.",
    "license":  "Other proprietary",
    "website":  "https://store.webkul.com/Odoo-POS-Keyboard-Shortcuts.html",
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
    "live_test_url":  "http://odoodemo.webkul.com/?module=pos_keyboard_shortcut&custom_url=/pos/web",
    "depends":  ['point_of_sale'],
    "data":  [
        'security/ir.model.access.csv',
        'views/pos_keyboard_shortcuts_view.xml',
        'views/pos_config_view.xml',
        'views/template.xml',
    ],
    "demo":  ['demo/demo.xml'],
    "qweb":  ['static/src/xml/pos.xml'],
    "images":  ['static/description/Banner.png'],
    "application":  True,
    "installable":  True,
    "auto_install":  False,
    "price":  49,
    "currency":  "USD",
    "pre_init_hook":  "pre_init_check",
}
