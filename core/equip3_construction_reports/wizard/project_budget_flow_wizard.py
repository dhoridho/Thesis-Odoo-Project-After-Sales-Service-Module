from odoo import api, models, fields, _


class ProjectBudgetFlowWizard(models.TransientModel):
    _name = 'project.budget.flow.wizard'
    _description = 'Project Budget Flow Wizard'

    name = fields.Char(string='Name', default='Project Budget Flow')

    def button_add_product(self):
        action = self.env.ref('sale.product_template_action').read()[0]
        return action

    def button_group_of_product(self):
        action = self.env.ref('equip3_construction_masterdata.action_view_group_of_product_menu_tree').read()[0]
        return action

    def button_uom(self):
        action = self.env.ref('uom.product_uom_form_action').read()[0]
        return action
    
    def button_variable(self):
        action = self.env.ref('equip3_construction_masterdata.variable_estimation_action').read()[0]
        return action

    def button_job_subcon(self):
        action = self.env.ref('equip3_construction_masterdata.variable_subcon_action').read()[0]
        return action

    def button_cost_sheet(self):
        action = self.env.ref('equip3_construction_operation.action_view_job_cost_sheet_menu').read()[0]
        return action

    def button_project_budget_transfer(self):
        action = self.env.ref('equip3_construction_operation.project_budget_transfer_menu_action').read()[0]
        return action

    def button_budget_change_request(self):
        action = self.env.ref('equip3_construction_operation.budget_change_request_menu_action').read()[0]
        return action

    def button_project_budget(self):
        action = self.env.ref('equip3_construction_operation.project_budget_action').read()[0]
        return action

    def button_budget_transfer(self):
        action = self.env.ref('equip3_construction_operation.budget_transfer_menu_action').read()[0]
        return action

    def button_cost_progress(self):
        action = self.env.ref('equip3_construction_reports.action_cost_progress_analysis').read()[0]
        return action

    def button_scurve(self):
        action = self.env.ref('equip3_construction_reports.action_s_curve').read()[0]
        return action
    
    def button_gantt_chart(self):
        action = self.env.ref('equip3_construction_reports.action_view_gantt_report_cons').read()[0]
        return action
    
    def button_issue_analysis(self):
        action = self.env.ref('equip3_construction_reports.action_issue_analysis').read()[0]
        return action

    def button_project_progress(self):
        action = self.env.ref('equip3_construction_reports.project_progress_report_action').read()[0]
        return action

    def button_claim_customer(self):
        action = self.env.ref('equip3_construction_reports.progressive_claim_customer_report_action').read()[0]
        return action

    def button_claim_subcon(self):
        action = self.env.ref('equip3_construction_reports.progressive_claim_subcon_report_action').read()[0]
        return action