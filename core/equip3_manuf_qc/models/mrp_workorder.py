from odoo import models, fields, api, _


class MrpWorkorder(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'sh.mrp.qc.reuse']

    move_point_ids = fields.One2many('sh.qc.move.point', 'workorder_id', string='Move Points', readonly=True)

    def create_consumption(self, confirm_and_assign=False):
        consumption_id = super(MrpWorkorder, self).create_consumption(confirm_and_assign=confirm_and_assign)
        consumption_moves =  consumption_id.move_raw_ids | consumption_id.byproduct_ids | consumption_id.move_finished_ids
        consumption_move_points = self.move_point_ids.filtered(lambda m: m.move_id in consumption_moves)
        consumption_id.move_point_ids = [(6, 0, consumption_move_points.ids)]
        for move in consumption_moves:
            if move.qc_check_ids:
                move.qc_check_ids.write({'sh_consumption_id': consumption_id.id})
            if move.qc_alert_ids:
                move.qc_alert_ids.write({'consumption_id': consumption_id.id})
        return consumption_id
