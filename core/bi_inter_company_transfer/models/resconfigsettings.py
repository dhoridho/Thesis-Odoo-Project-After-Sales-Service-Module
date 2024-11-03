# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    validate_picking = fields.Boolean('Validate Receipt/picking in so/po ')
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po')
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po')
    allow_auto_intercompany = fields.Boolean('Allow Auto Intercompany Transaction')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'validate_picking': self.env.company.validate_picking,
            'create_invoice': self.env.company.create_invoice,
            'validate_invoice': self.env.company.validate_invoice,
            'allow_auto_intercompany': self.env.company.allow_auto_intercompany
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env.company.write({
            'validate_picking': self.validate_picking,
            'create_invoice': self.create_invoice,
            'validate_invoice': self.validate_invoice,
            'allow_auto_intercompany': self.allow_auto_intercompany
        })

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: