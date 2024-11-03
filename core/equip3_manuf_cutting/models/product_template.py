from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_cutting_product = fields.Boolean(string="Is a Cutting Product")
    cutting_unit_measure = fields.Many2one('uom.uom', string='Cutting Unit of Measure')
    check_cutting = fields.Boolean(string="Cutting", related="equi3_company_id.cutting", readonly=False)
    equi3_company_id = fields.Many2one('res.company', string='Cutting Company', default=lambda self: self.env.company)
