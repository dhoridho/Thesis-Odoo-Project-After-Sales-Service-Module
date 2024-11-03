# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class Inventory(models.Model):
    _inherit = "stock.inventory"

    def _get_inventory_lines_values(self):
        res = super(Inventory, self)._get_inventory_lines_values()
        for line in res:
            if 'product_qty' in line:
                line['product_qty'] = 0
        return res
