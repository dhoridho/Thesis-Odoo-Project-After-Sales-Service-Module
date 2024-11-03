from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    qc_point_ids = fields.Many2many('sh.qc.point', string='Quality Points')
    qc_check_ids = fields.One2many('sh.mrp.quality.check', 'move_id', string='Quality Checks')
    qc_alert_ids = fields.One2many('sh.mrp.quality.alert', 'move_id', string='Quality Alerts')

    applied_point_ids = fields.Many2many('sh.qc.point', 'stock_move_applied_point_rel', string='Applied Points')
