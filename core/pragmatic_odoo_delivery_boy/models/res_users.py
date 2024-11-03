# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class ResUsersInherit(models.Model):
    _inherit = 'res.users'
    
    device_token = fields.Char(string="Device Token", help='Used to show notification')

    @api.model
    def create(self, vals):
        res = super(ResUsersInherit, self).create(vals)
        if res.has_group('pragmatic_odoo_delivery_boy.group_pragtech_driver'):
            res.partner_id.is_driver = True
        else:
            res.partner_id.is_driver = False
        return res

    def set_is_driver(self):
        for rec in self:
            if rec.has_group('pragmatic_odoo_delivery_boy.group_pragtech_driver'):
                rec.partner_id.is_driver = True
            else:
                rec.partner_id.is_driver = False

    def write(self, vals):
        res = super(ResUsersInherit, self).write(vals)
        self.set_is_driver()
        return res
