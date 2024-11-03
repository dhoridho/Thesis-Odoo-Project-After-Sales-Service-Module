from odoo import api, fields, models, _

class StocKmove(models.Model):
    _inherit = 'stock.move'
    
    mwo_id = fields.Many2one(comodel_name='maintenance.work.order', string='Work Order')
