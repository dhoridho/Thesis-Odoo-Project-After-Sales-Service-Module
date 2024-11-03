# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        if res.opportunity_id:
            if not res.opportunity_id.quotation_date and not res.opportunity_id.quotation_day:
                res.opportunity_id.write({
                    'quotation_date': fields.Datetime.now(),
                    'quotation_day': (fields.Datetime.now() - res.opportunity_id.create_date).days
                })
        return res