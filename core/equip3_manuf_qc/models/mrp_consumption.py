from odoo import models, fields, api


class MrpConsumption(models.Model):
    _name = 'mrp.consumption'
    _inherit = ['mrp.consumption', 'sh.mrp.qc.reuse']

    move_point_ids = fields.One2many('sh.qc.move.point', 'consumption_id', string='Move Points', readonly=True)
