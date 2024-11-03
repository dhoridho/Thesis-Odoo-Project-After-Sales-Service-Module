# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api,_
from odoo.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if 'is_customer' in vals and vals.get('is_customer'):
            customer_group = self.env.ref('equip3_purchase_vendor_portal.group_customer_user')
            vendor_group = self.env.ref('equip3_purchase_vendor_portal.group_vendor_user')
            user_ids = self.user_ids and self.user_ids[0].id or False
            if user_ids:
                customer_group.sudo().write({
                    'users': [(4, user_ids)]
                })
                vendor_group.sudo().write({
                    'users': [(3, user_ids)]
                })
        elif 'is_vendor' in vals and vals.get('is_vendor'):
            customer_group = self.env.ref('equip3_purchase_vendor_portal.group_customer_user')
            vendor_group = self.env.ref('equip3_purchase_vendor_portal.group_vendor_user')
            user_ids = self.user_ids and self.user_ids[0].id or False
            if user_ids:
                vendor_group.sudo().write({
                    'users': [(4, user_ids)]
                })
                customer_group.sudo().write({
                    'users': [(3, user_ids)]
                })
        return res
