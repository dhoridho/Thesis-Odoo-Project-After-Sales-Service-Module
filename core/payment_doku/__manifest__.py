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
  "name"                 :  "Doku Payment Acquirer",
  "summary"              :  """Integrate Doku Payment Gateway with Odoo. Using this module, your customers can pay for their online orders with DOku payment gateway on Odoo website.""",
  "category"             :  "Website",
  "version"              :  "1.1.1",
  "sequence"             :  1,
  "author"               :  "Webkul Software Pvt. Ltd.",
  "license"              :  "Other proprietary",
  "maintainer"           :  "Saurabh Gupta",
  "website"              :  "https://store.webkul.com/Odoo-Doku-Payment-Acquirer.html",
  "description"          :  """Odoo Doku Stripe Payment Acquirer
Odoo Doku Payment Gateway
Payment Gateway
Doku
Doku integration
Payment acquirer
Payment processing
Payment processor
Website payments
Sale orders payment
Customer payment
Integrate Doku payment acquirer in Odoo
Integrate Doku payment gateway in Odoo""",
  "depends"              :  [
                             'payment',
                             'website_sale',
                            ],
  "data"                 :  [
                             'views/payment_view.xml',
                             'views/doku_acquirer_data.xml',
                             'views/payment_template.xml',
                             'data/demo_doku.xml',
                            ],
  "demo"                 :  [],
  "images"               :  ['static/description/banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "price"                :  69.0,
  "currency"             :  "USD",
  "post_init_hook"       :  "create_missing_journal_for_acquirers",
}
