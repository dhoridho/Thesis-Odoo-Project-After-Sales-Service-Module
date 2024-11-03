from odoo import api, fields, models, _


class MrpApprovalMatrix(models.Model):
    _inherit = 'mrp.approval.matrix'

    matrix_type = fields.Selection(selection_add=[('pr', 'Production Record')])

    def get_model_action_xmlid(self):
        if self.matrix_type != 'pr':
            return super(MrpApprovalMatrix, self).get_model_action_xmlid()
        return 'equip3_manuf_operations_contd.action_mrp_consumption'

    def get_model_menu_xmlid(self):
        if self.matrix_type == 'pr':
            return super(MrpApprovalMatrix, self).get_model_menu_xmlid()
        return 'equip3_manuf_operations_contd.menu_mrp_consumption'


class MrpApprovalMatrixEntry(models.Model):
    _inherit = 'mrp.approval.matrix.entry'

    pr_id = fields.Many2one(comodel_name='mrp.consumption', string='Production Record')
