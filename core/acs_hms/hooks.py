# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

#ACS: Remove in odoo15 if not used anymore
def pre_init_hook(cr):
    # env = api.Environment(cr, SUPERUSER_ID, {})
    # try:
    #     env['stock.warehouse.orderpoint'].search([]).toggle_active()
    #     env['product.template'].search([]).toggle_active()
    # except:
    #     pass
    pass
