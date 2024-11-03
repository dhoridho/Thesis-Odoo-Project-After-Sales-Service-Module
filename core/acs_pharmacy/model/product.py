# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    #ACS: Remove manufacturer as drug_company field is already there in base.
    manufacturer = fields.Many2one('res.partner', 'Manufacturer')
    manufacturer_pname = fields.Char('Product Name')
    manufacturer_pref = fields.Char('Product Code')
    manufacturer_purl = fields.Char('Product URL')


class ProductCategory(models.Model):
    _inherit = 'product.category'

    lot_default_locked = fields.Boolean(string='Block new Serial Numbers/lots',
        help='If checked, future Serial Numbers/lots will be created blocked by default')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: