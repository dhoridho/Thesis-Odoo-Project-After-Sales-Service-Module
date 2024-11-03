# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    intercompany_warehouse_id = fields.Many2one('stock.warehouse',string="Intercompany Warehouse")
    validate_picking = fields.Boolean('Validate Receipt/picking in so/po ' , default = False)
    create_invoice = fields.Boolean('Create Invoice/Bill in so/po ' , default = False)
    validate_invoice = fields.Boolean('Validate Invoice/Bill in so/po ' , default = False)
    allow_auto_intercompany = fields.Boolean('Allow Auto Intercompany Transaction' , default = False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: