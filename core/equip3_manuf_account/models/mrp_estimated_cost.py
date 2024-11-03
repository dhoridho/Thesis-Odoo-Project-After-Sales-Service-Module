from odoo import models, fields, api, _


class MrpEstimatedCost(models.Model):
    _name = 'mrp.estimated.cost'
    _description = 'MRP Estimated Cost'

    company_id = fields.Many2one('res.company', string='Company', related='production_id.company_id')
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    name = fields.Char()
    qty = fields.Float(string='Quantity')
    uom_name = fields.Char()
    total_cost = fields.Monetary(string='Total Cost')

    # technical fields
    level = fields.Integer(string='Level')
    type = fields.Selection(selection=[
        ('finished', 'Finished Goods'), 
        ('byproduct', 'By-Product'),
        ('component', 'Material'),
        ('overhead', 'Overhead'),
        ('labor', 'Labor')
    ], string='Type', required=True)
    product_id = fields.Many2one('product.product')
    operation_id = fields.Many2one('mrp.routing.workcenter')
    user_id = fields.Many2one('res.users')
    product_qty = fields.Float(digits='Product Unit of Measure', string='Product Quantity')

    """ These fields has nothing to do with each other, simply just for o2m relation purposes """
    production_id = fields.Many2one('mrp.production', string='Production Order')
    plan_id = fields.Many2one('mrp.plan', string='Production Plan')

    @api.depends('dummy_uom', 'product_uom')
    def _compute_uom_name(self):
        for record in self:
            record.uom_name = record.dummy_uom or record.product_uom.display_name
