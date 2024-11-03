from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _inherit = ['mrp.production', 'sh.mrp.qc.reuse']

    qc_state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('failed', 'Failed'),
            ('passed', 'Passed')],
        string='QC State', compute='compute_qc_state', store=True)

    move_point_ids = fields.One2many('sh.qc.move.point', 'production_id', string='Move Points', readonly=True)

    @api.depends('qc_fail', 'qc_pass', 'pending_qc', 'need_qc')
    def compute_qc_state(self):
        self.filtered(lambda s: s.qc_fail).qc_state = 'failed'
        self.filtered(lambda s: s.qc_pass).qc_state = 'passed'
        self.filtered(lambda s: not s.qc_fail and not s.qc_pass).qc_state = 'pending'
    
    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        for record in self:
            record._set_qc_move_points()
        return res

    def _set_qc_move_points(self):
        self.ensure_one()
        move_point_values = [(5,)]
        for move in self.move_raw_ids | self.move_finished_ids:
            for point in move.qc_point_ids:
                move_point_values += [(0, 0, {
                    'plan_id': self.mrp_plan_id and self.mrp_plan_id.id or False,
                    'production_id': self.id,
                    'move_id': move.id,
                    'point_id': point.id,
                    'remaining_check': point.number_of_test
                })]
        self.move_point_ids = move_point_values
        for workorder in self.workorder_ids:
            workorder_moves = workorder.move_raw_ids | workorder.byproduct_ids | workorder.move_finished_ids
            workorder_move_points = self.move_point_ids.filtered(lambda m: m.move_id in workorder_moves)
            workorder.move_point_ids = [(6, 0, workorder_move_points.ids)]

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        values = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)
        if bom_line is False:
            return values
        values['qc_point_ids'] = [(6, 0, bom_line.quality_point_ids.ids)]
        return values

    def _get_move_finished_values(self, product_id, product_uom_qty, product_uom, operation_id=False, byproduct_id=False):
        values = super(MrpProduction, self)._get_move_finished_values(product_id, product_uom_qty, product_uom, operation_id, byproduct_id)
        if byproduct_id:
            return values
        operation_ids = self.bom_id.operation_ids
        values['qc_point_ids'] = [(6, 0, operation_ids.mapped('quality_point_ids').ids)]
        return values

    def button_mark_done(self):
        for record in self:
            record.check_mandatory_qc()
        return super(MrpProduction, self).button_mark_done()
