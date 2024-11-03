# -*- coding: utf-8 -*-
{
    'name': "Equip3 - POS Printer Bluetooth.",
    'support': "support@easyerps.com",
    'license': "OPL-1",
    'price': 295,
    'currency': "USD",
    'summary': """
        This module Allows you to print POS receipts and Bar/Restaurant bills directly using Bluetooth, Built-in, USB or IP Printer on SUNMI/Android devices
        """,
    'author': "EasyERPS",
    'website': "https://EasyERPS.com",
    'category': 'Point of Sale',
    'version': '1.1.7',
    'depends': ['base', 'point_of_sale', 'pos_restaurant','equip3_pos_general'],
    'data': [
        'views/assets.xml',
        'views/restaurant_printer_views.xml',
        'views/pos_config_views.xml',
    ],

    'qweb': [
        # 'static/src/xml/Chrome.xml',
        'static/src/xml/GategoryReceipt.xml',
        'static/src/xml/KitchenReceiptScreen.xml',
        'static/src/xml/LabelReceipt.xml',
        'static/src/xml/ReceiptScreen.xml',
        'static/src/xml/ReprintReceiptScreen.xml',
        # 'static/src/xml/TicketScreen.xml',

    ],

    'images': ['images/main_screenshot.png'],
}
