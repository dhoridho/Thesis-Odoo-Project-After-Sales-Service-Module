from odoo import models, fields, api


class MovePoint(models.Model):
    _name = 'sh.qc.move.point'
    _description = 'Pair Move Point'

    @api.depends('move_id')
    def _compute_move_type(self):
        for record in self:
            move_id = record.move_id
            if move_id.bom_line_id:
                move_type = 'material'
            elif move_id.byproduct_id:
                move_type = 'byproduct'
            else:
                move_type = 'finished'
            record.move_type = move_type

    plan_id = fields.Many2one('mrp.plan', string='Production Plan')
    production_id = fields.Many2one('mrp.production', string='Production Order')
    workorder_id = fields.Many2one('mrp.workorder', string='Workorder')
    consumption_id = fields.Many2one('mrp.consumption', string='Production Record')
    move_id = fields.Many2one('stock.move', string='Move')
    point_id = fields.Many2one('sh.qc.point', string='Point')
    remaining_check = fields.Integer(string='Remaining Check')
    move_type = fields.Selection(
        selection=[
            ('material', 'Material'),
            ('byproduct', 'ByProduct'),
            ('finished', 'Finished Goods')
        ],
        string='Move Type',
        compute=_compute_move_type
    )