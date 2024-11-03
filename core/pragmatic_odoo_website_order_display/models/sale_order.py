from odoo import api, fields, models, tools, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection(selection_add=[
        ('progress', 'In Progress'),
        ('ready', 'Ready'),
        ('picked', 'Picked'),
        ('delivered', 'Delivered'),
        ('done',)
        ], string='Status', readonly=True, copy=False, index=True, tracking=3)


    def action_start(self):
        return self.write({'state': 'progress'})

    def action_complete(self):
        return self.write({'state': 'ready'})