from odoo import api , fields , models


class ResCompany(models.Model):
    _inherit = 'res.company'

    construction = fields.Boolean(string="Construction")
    construction_sales = fields.Boolean(string="Construction Sales")
    construction_project = fields.Boolean(string='Construction Project')
    construction_accounting = fields.Boolean(string='Construction Accounting')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    construction = fields.Boolean(string="Construction", related='company_id.construction', readonly=False)
    construction_sales = fields.Boolean(string="Sales", related='company_id.construction_sales', readonly=False)
    temp_const = fields.Boolean(string="Sales", readonly=False)
    is_customer_approval_matrix_const = fields.Boolean(string="Sale Order Approval Matrix")
    is_job_estimate_approval_matrix = fields.Boolean(string="BOQ Approval Matrix")
    construction_project = fields.Boolean(string='Project', related='company_id.construction_project', readonly=False)
    is_project_budget_approval_matrix = fields.Boolean(string='Periodical Budget Approval Matrix')
    cost_sheet_approval_matrix = fields.Boolean(string="Cost Sheet Approval Matrix")
    budget_change_request_approval_matrix = fields.Boolean(string='Budget Change Request Approval Matrix')
    budget_carry_over_approval_matrix = fields.Boolean(string='Budget Carry Over Approval Matrix')
    project_budget_transfer_approval_matrix = fields.Boolean(string='Project Budget Transfer Approval Matrix')
    construction_accounting = fields.Boolean(string='Accounting', related='company_id.construction_accounting', readonly=False)
    is_claim_request_approval_matrix = fields.Boolean(string='Claim Request Approval Matrix')
    is_progress_history_approval_matrix = fields.Boolean(string='Progress History Approval Matrix')
    is_asset_allocation_approval_matrix = fields.Boolean(string='Asset Allocation Approval Matrix')
    is_change_allocation_approval_matrix = fields.Boolean(string='Change Allocation Budget Approval Matrix')
    is_create_default_analytic_group = fields.Boolean(string='Default Analytic Group')
    cons_use_code = fields.Boolean(string='Use Code')
    is_custom_project_progress = fields.Boolean(string='Progress Compute Options')
    is_multiple_budget_procurement = fields.Boolean(string='Multiple Budget')

    @api.onchange('construction')
    def onchange_construction(self):
        for rec in self:
            if rec.construction == False:
                rec.is_customer_approval_matrix_const = False
                rec.is_job_estimate_approval_matrix = False
                rec.cost_sheet_approval_matrix = False
                rec.is_project_budget_approval_matrix = False
                rec.budget_change_request_approval_matrix = False
                rec.project_budget_transfer_approval_matrix = False
                rec.is_progress_history_approval_matrix = False
                rec.budget_carry_over_approval_matrix = False
                rec.is_claim_request_approval_matrix = False
                rec.is_asset_allocation_approval_matrix = False
                rec.is_change_allocation_approval_matrix = False

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_customer_approval_matrix_const = IrConfigParam.get_param('is_customer_approval_matrix_const')
        if is_customer_approval_matrix_const is None:
            is_customer_approval_matrix_const = True
        is_job_estimate_approval_matrix = IrConfigParam.get_param('is_job_estimate_approval_matrix')
        if is_job_estimate_approval_matrix is None:
            is_job_estimate_approval_matrix = True
        is_claim_request_approval_matrix = IrConfigParam.get_param('is_claim_request_approval_matrix')
        if is_claim_request_approval_matrix is None:
            is_claim_request_approval_matrix = True
        cost_sheet_approval_matrix = IrConfigParam.get_param('cost_sheet_approval_matrix')
        if cost_sheet_approval_matrix is None:
            cost_sheet_approval_matrix = True
        is_progress_history_approval_matrix = IrConfigParam.get_param('is_progress_history_approval_matrix')
        if is_progress_history_approval_matrix is None:
            is_progress_history_approval_matrix = True
        is_project_budget_approval_matrix = IrConfigParam.get_param('is_project_budget_approval_matrix')
        if is_project_budget_approval_matrix is None:
            is_project_budget_approval_matrix = True
        budget_change_request_approval_matrix = IrConfigParam.get_param('budget_change_request_approval_matrix')
        if budget_change_request_approval_matrix is None:
            budget_change_request_approval_matrix = True
        project_budget_transfer_approval_matrix = IrConfigParam.get_param('project_budget_transfer_approval_matrix')
        if project_budget_transfer_approval_matrix is None:
            project_budget_transfer_approval_matrix = True
        budget_carry_over_approval_matrix = IrConfigParam.get_param('budget_carry_over_approval_matrix')
        if budget_carry_over_approval_matrix is None:
            budget_carry_over_approval_matrix = True
        is_asset_allocation_approval_matrix = IrConfigParam.get_param('is_asset_allocation_approval_matrix')
        if is_asset_allocation_approval_matrix is None:
            is_asset_allocation_approval_matrix = True
        is_change_allocation_approval_matrix = IrConfigParam.get_param('is_change_allocation_approval_matrix')
        if is_change_allocation_approval_matrix is None:
            is_change_allocation_approval_matrix = True
        construction = IrConfigParam.get_param('construction', False)
        is_create_default_analytic_group = IrConfigParam.get_param('is_create_default_analytic_group', False)
        cons_use_code = IrConfigParam.get_param('cons_use_code', False)
        is_custom_project_progress = IrConfigParam.get_param('is_custom_project_progress', False)
        is_multiple_budget_procurement = IrConfigParam.get_param('is_multiple_budget_procurement', False)
        res.update({
            'is_customer_approval_matrix_const': is_customer_approval_matrix_const,
            'is_job_estimate_approval_matrix': is_job_estimate_approval_matrix,
            'is_project_budget_approval_matrix': is_project_budget_approval_matrix,
            'budget_change_request_approval_matrix': budget_change_request_approval_matrix,
            'project_budget_transfer_approval_matrix': project_budget_transfer_approval_matrix,
            'budget_carry_over_approval_matrix': budget_carry_over_approval_matrix,
            'is_progress_history_approval_matrix': is_progress_history_approval_matrix,
            'is_claim_request_approval_matrix': is_claim_request_approval_matrix,
            'cost_sheet_approval_matrix': cost_sheet_approval_matrix,
            'is_asset_allocation_approval_matrix': is_asset_allocation_approval_matrix,
            'is_change_allocation_approval_matrix': is_change_allocation_approval_matrix,
            'construction': construction,
            'is_create_default_analytic_group': is_create_default_analytic_group,
            'cons_use_code': cons_use_code,
            'is_custom_project_progress': is_custom_project_progress,
            'is_multiple_budget_procurement': is_multiple_budget_procurement,
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values() 
        self.env['ir.config_parameter'].sudo().set_param('is_customer_approval_matrix_const', self.is_customer_approval_matrix_const)
        self.env['ir.config_parameter'].sudo().set_param('is_job_estimate_approval_matrix', self.is_job_estimate_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_project_budget_approval_matrix', self.is_project_budget_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('budget_change_request_approval_matrix', self.budget_change_request_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('project_budget_transfer_approval_matrix', self.project_budget_transfer_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_progress_history_approval_matrix', self.is_progress_history_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_claim_request_approval_matrix', self.is_claim_request_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('cost_sheet_approval_matrix', self.cost_sheet_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('budget_carry_over_approval_matrix', self.budget_carry_over_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_asset_allocation_approval_matrix', self.is_asset_allocation_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_change_allocation_approval_matrix', self.is_change_allocation_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('construction', self.construction)
        self.env['ir.config_parameter'].sudo().set_param('is_create_default_analytic_group', self.is_create_default_analytic_group)
        self.env['ir.config_parameter'].sudo().set_param('cons_use_code', self.cons_use_code)
        self.env['ir.config_parameter'].sudo().set_param('is_custom_project_progress', self.is_custom_project_progress)
        self.env['ir.config_parameter'].sudo().set_param('is_multiple_budget_procurement', self.is_multiple_budget_procurement)



