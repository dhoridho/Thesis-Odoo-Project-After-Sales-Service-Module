from numpy import matrix
from odoo import models, fields, api, _


class MrpApprovalMatrix(models.Model):
    _inherit = 'mrp.approval.matrix'

    matrix_type = fields.Selection(
        selection_add=[
            ('cp', 'Cutting Plan'),
            ('co', 'Cutting Order')
        ])

    def get_model_action_xmlid(self):
        if self.matrix_type == 'cp':
            return 'equip3_manuf_cutting.action_view_cutting_plan'
        elif self.matrix_type == 'co':
            return 'equip3_manuf_cutting.action_view_cutting_order'
        return super(MrpApprovalMatrix, self).get_model_action_xmlid()

    def get_model_menu_xmlid(self):
        if self.matrix_type == 'cp':
            return 'equip3_manuf_cutting.mrp_cutting_plan'
        elif self.matrix_type == 'co':
            return 'equip3_manuf_cutting.mrp_cutting_order'
        return super(MrpApprovalMatrix, self).get_model_menu_xmlid()


class MrpApprovalMatrixEntry(models.Model):
    _inherit = 'mrp.approval.matrix.entry'

    cp_id = fields.Many2one(comodel_name='cutting.plan', string='Cutting Plan')
    co_id = fields.Many2one(comodel_name='cutting.order', string='Cutting Order')
