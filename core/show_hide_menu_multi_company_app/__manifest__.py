# -*- coding: utf-8 -*-

{
    'name': 'Hide Menu on Multi Company for Users',
    "author": "Edge Technologies",
    'version': '1.1.1',
    'live_test_url': "https://youtu.be/21FIpMU24TU",
    "images":['static/description/main_screenshot.png'],
    'summary': "Company show hide menu feature user hide menu from user limited menu access to user multi company menu restriction to user multi company show hide feature multi company show hide menu feature multi company user hide menu multi company hide menu from user",
    'description': """ This app will allow to hide main Menus and also sub Menus.
        Menu or sub menu will invisible for particular company and for particular users.

   
   Menu Hide/Show for User in Odoo Hide menu for user in Odoo show menu for user. Visible and Invisible menu for user in Odoo.
   User Generic Security Restriction for menu in odoo. Odoo Hide menu by security groups in odoo Hide menu from a specific user.
    Restrict menu from a specific user. Hide Any menu for user in Odoo Restrict User Menus in Odoo from Settings. Odoo User Menu Restriction.
    hide any menu and submenu for specific user. Security for Menu and submenu. Display or Hide particular menu for specific user

show hide feature
show hide menu feature
user hide menu 
hide menu from user 
limied menu access to user
restricted menu access to user
menu wise restricion
show menu to user

multi company menu restriction to user
multi company show hide feature
multi company show hide menu feature
multi company user hide menu 
multi companyhide menu from user 
multi company limited menu access to user
multi company restricted menu access to user
multi company menu wise restricion
multi company show menu to user
multi company menu restriction to user
Generic Security Restriction 
mutli-company Security Restriction
multiple company Generic Security Restriction

 
    """,
    "license" : "OPL-1",
    'depends': ['base','sale_management','purchase','stock'],
    'data': [
            'security/hide_menu_security.xml',
            'security/ir.model.access.csv',
            'views/view_main_hide.xml',
            ],
    'installable': True,
    'auto_install': False,
    'price': 10,
    'currency': "EUR",
    'category': 'Extra Tools',
    
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
