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
  "name"                 :  "POS All Orders List",
  "summary"              :  """The module shows the list of orders placed in a Odoo POS screen. The user can also view previous orders from one customers in running POS session""",
  "category"             :  "Point of Sale",
  "version"              :  "1.1.2",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "website"              :  "https://store.webkul.com/Odoo-POS-All-Orders-List.html",
  "description"          :  """Odoo POS All Orders List
Customer orders list
All POS orders
POS order list
POS Customers orders
Reorder list
POS Load previous orders
Past orders pos
Pos past orders
Orders POS session""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=pos_orders&custom_url=/pos/auto",
  "depends"              :  ['point_of_sale'],
  "data"                 :  [
                             'views/pos_config_view.xml',
                             'views/template.xml',
                            ],
  "demo"                 :  ['data/pos_orders_demo.xml'],
  "qweb"                 :  ['static/src/xml/pos_orders.xml'],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
  "price"                :  27,
  "currency"             :  "USD",
  "pre_init_hook"        :  "pre_init_check",
}