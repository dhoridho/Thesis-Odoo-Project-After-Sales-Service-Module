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
  "name"                 :  "Website Webkul Addons",
  "summary"              :  """Website Webkul Addons allows Odoo users to manage all Webkul’s Odoo website Related modules from single page.""",
  "category"             :  "Hidden",
  "version"              :  "1.1.1",
  "author"               :  "Webkul Software Pvt. Ltd.",
  "website"              :  "https://store.webkul.com/Odoo.html",
  "description"          :  """Website Webkul Addons
Webkul
Addons
Website Addons
Webkul Addons
Webkul Website Modules
Webkul Module
Modules
Webkul Addons For Website""",
  "live_test_url"        :  "http://odoodemo.webkul.com/?module=website_webkul_addons",
  "depends"              :  ['website'],
  "data"                 :  [
                            'security/ir.model.access.csv',
                             'wizard/wk_website_wizard_view.xml',
                             'views/webkul_addons_config_view.xml',
                            ],
  "images"               :  ['static/description/Banner.png'],
  "application"          :  True,
  "installable"          :  True,
  "auto_install"         :  False,
}