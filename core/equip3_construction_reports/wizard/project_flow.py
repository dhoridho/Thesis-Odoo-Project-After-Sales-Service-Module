from odoo import api, models, fields, _


class ProjectFlowWizard(models.TransientModel):
    _name = 'construction.project.flow.wizard'
    _description = 'Construction Project Flow Wizard'

    name = fields.Char(string='Name', default='Construction Flow')

    def button_customer(self):
        action = self.env.ref('account.res_partner_action_customer').read()[0]
        return action
    
    def button_stage(self):
        action = self.env.ref('project.open_task_type_form').read()[0]
        return action

    def button_type_issue(self):
        action = self.env.ref('abs_construction_management.action_view_issue_type_menu_tree').read()[0]
        return action
    
    def button_issue_stage(self):
        action = self.env.ref('equip3_construction_operation.issue_stage_action').read()[0]
        return action

    def button_tags(self):
        action = self.env.ref('project.project_tags_action').read()[0]
        return action

    def button_activity(self):
        action = self.env.ref('project.mail_activity_type_action_config_project_types').read()[0]
        return action

    def button_project_template(self):
        action = self.env.ref('equip3_construction_operation.template_project_action').read()[0]
        return action

    def button_job_template(self):
        action = self.env.ref('equip3_construction_operation.job_order_template_action').read()[0]
        return action

    def button_progress_matrix(self):
        action = self.env.ref('equip3_construction_operation.action_approval_matrix_progress_history').read()[0]
        return action

    def button_project(self):
        action = self.env.ref('abs_construction_management.action_view_project').read()[0]
        return action

    def button_job_orders(self):
        action = self.env.ref('equip3_construction_reports.action_view_task_inherited_flow').read()[0]
        return action
    
    def button_subtask(self):
        action = self.env.ref('equip3_construction_reports.action_view_task_inherited_subtask_flow').read()[0]
        return action
    
    def button_material_usage(self):
        action = self.env.ref('equip3_construction_operation.action_stock_product_usage').read()[0]
        return action

    def button_progress_history(self):
        action = self.env.ref('equip3_construction_operation.progress_history_action').read()[0]
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