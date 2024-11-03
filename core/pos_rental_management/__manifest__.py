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
    "name":  "POS Rental Management",
    "summary":  "This module is used to sell product on rental basis from the pos.Rental Management|Management|Rental|Custom Rental Management",
    "category":  "Point of Sale",
    "version":  "1.1.1",
    "sequence":  1,
    "author":  "Webkul Software Pvt. Ltd.",
    "license":  "Other proprietary",
    "website":  "https://store.webkul.com/",
    "live_test_url":  "http://odoodemo.webkul.com/?module=pos_rental_management&custom_url=/pos/auto",
    "depends":  ['point_of_sale'],
    "data":  [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'data/data.xml',
        'views/inherit_res_config_settings_views.xml',
        'views/inherit_pos_config_view.xml',
        'views/inherit_account_move_view.xml',
        'views/inherit_pos_order.xml',
        'views/inherit_product_template_view.xml',
        'views/pos_menus.xml',
        'views/rental_pos_order_view.xml',
    ],
    "qweb":  [
        'static/src/xml/pos_rental.xml',
        'static/src/xml/posRentalPopUp.xml',
        'static/src/xml/rental_pos_orders.xml'
    ],
    "images":  ['static/description/banner.gif'],
    "application":  True,
    "installable":  True,
    "auto_install":  False,
    "price":  149,
    "currency":  "USD",
    "pre_init_hook":  "pre_init_check",
}
