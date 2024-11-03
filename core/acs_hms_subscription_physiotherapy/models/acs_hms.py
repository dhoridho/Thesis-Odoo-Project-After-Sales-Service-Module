# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Physiotherapy(models.Model):
    _inherit = 'acs.physiotherapy'

    subscription_id = fields.Many2one("acs.hms.subscription", "Subscription", ondelete="restrict")

    @api.onchange("subscription_id")
    def onchange_subscription_id(self):
        if self.subscription_id:
            if self.subscription_id.acs_type=='full':
                self.no_invoice = True
            else:
                self.pricelist_id = self.subscription_id.pricelist_id and self.subscription_id.pricelist_id.id or False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: