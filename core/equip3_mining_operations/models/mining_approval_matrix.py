from odoo import models, fields, api, _


class MiningApprovalMatrix(models.Model):
    _inherit = 'mining.approval.matrix'

    matrix_type = fields.Selection(
        selection=[
            ('msc', 'Mining Site Control'),
            ('mpc', 'Mining Pit Control'),
            ('mdp', 'Mining Daily Production'),
            ('mpp', 'Mining Production Plan'),
            ('mpl', 'Mining Production Line'),
            ('mpa', 'Mining Production Actualization')
        ],
        copy=False,
        string='Matrix Type',
        default='mp',
        tracking=True)

    _sql_constraints = [
        ('unique_mining_approval_matrix', 'unique(company_id, branch_id, matrix_type)', 'The branch already used for another Approval Matrix. Please choose another branch.')
    ]

    def get_model_action_xmlid(self):
        if self.matrix_type == 'msc':
            return 'equip3_mining_operations.mining_site_control_actions'
        elif self.matrix_type == 'mpc':
            return 'equip3_mining_operations.action_mining_project_control'
        elif self.matrix_type == 'mdp':
            return 'equip3_mining_operations.daily_production_actions'
        elif self.matrix_type == 'mpp':
            return 'equip3_mining_operations.mining_production_plan_action'
        elif self.matrix_type == 'mpl':
            return 'equip3_mining_operations.mining_production_line_action'
        elif self.matrix_type == 'mpa':
            return 'equip3_mining_operations.mining_production_act_action'
        return super(MiningApprovalMatrix, self).get_model_action_xmlid()

    def get_model_menu_xmlid(self):
        if self.matrix_type == 'msc':
            return 'equip3_mining_operations.mining_menu_control_site'
        elif self.matrix_type == 'mpc':
            return 'equip3_mining_operations.mining_menu_control_project'
        elif self.matrix_type == 'mdp':
            return 'equip3_mining_operations.mining_menu_operations_daily_production'
        elif self.matrix_type == 'mpp':
            return 'equip3_mining_operations.mining_production_plan_menu_act'
        elif self.matrix_type == 'mpl':
            return 'equip3_mining_operations.mining_production_line_menu_act'
        elif self.matrix_type == 'mpa':
            return 'equip3_mining_operations.mining_production_act_menu_act'
        return super(MiningApprovalMatrix, self).get_model_menu_xmlid()


class MiningApprovalMatrixLine(models.Model):
    _inherit = 'mining.approval.matrix.line'

    matrix_type = fields.Selection(related='matrix_id.matrix_type')


class MiningApprovalMatrixEntry(models.Model):
    _inherit = 'mining.approval.matrix.entry'

    matrix_type = fields.Selection(related='line_id.matrix_type')

    msc_id = fields.Many2one(comodel_name='mining.site.control', string='Mining Site')
    mpc_id = fields.Many2one(comodel_name='mining.project.control', string='Mining Pit')
    mdp_id = fields.Many2one(comodel_name='daily.production', string='Daily Production')
    mpp_id = fields.Many2one(comodel_name='mining.production.plan', string='Mining Production Plan')
    mpl_id = fields.Many2one(comodel_name='mining.production.line', string='Mining Production Line')
    mpa_id = fields.Many2one(comodel_name='mining.production.actualization', string='Mining Production Actualization')
