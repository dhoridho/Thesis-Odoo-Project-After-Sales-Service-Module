from odoo import models, fields, api, _


class AgriApprovalMatrix(models.Model):
    _inherit = 'agri.approval.matrix'

    matrix_type = fields.Selection(
        selection=[
            ('ada', 'Plantation Plan')
        ],
        copy=False,
        string='Matrix Type',
        default='mp',
        tracking=True)

    _sql_constraints = [
        ('unique_agri_approval_matrix', 'unique(company_id, branch_id, matrix_type)', 'The branch already used for another Approval Matrix. Please choose another branch.')
    ]

    def get_model_action_xmlid(self):
        if self.matrix_type == 'ada':
            return 'equip3_agri_operations.action_view_daily_activity'
        return super(AgriApprovalMatrix, self).get_model_action_xmlid()

    def get_model_menu_xmlid(self):
        if self.matrix_type == 'ada':
            return 'equip3_agri_operations.agri_agriculture_operation_daily_activity'
        return super(AgriApprovalMatrix, self).get_model_menu_xmlid()

    is_branch_required = fields.Boolean(related='company_id.show_branch')

class AgriApprovalMatrixLine(models.Model):
    _inherit = 'agri.approval.matrix.line'

    matrix_type = fields.Selection(related='matrix_id.matrix_type')


class AgriApprovalMatrixEntry(models.Model):
    _inherit = 'agri.approval.matrix.entry'
    
    matrix_type = fields.Selection(related='line_id.matrix_type')
    ada_id = fields.Many2one('agriculture.daily.activity', string='Agriculture Dailty Activity')
