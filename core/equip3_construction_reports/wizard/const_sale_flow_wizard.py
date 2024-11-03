from odoo import api, models, fields, _


class CRMSaleFlowWizard(models.TransientModel):
    _name = 'construction.sale.flow.wizard'
    _description = 'Construction Sale Flow Wizard'

    name = fields.Char(string='Name', default='Construction Sale Flow')

    def button_customer(self):
        action = self.env.ref('account.res_partner_action_customer').read()[0]
        return action

    def button_add_product(self):
        action = self.env.ref('sale.product_template_action').read()[0]
        return action

    def button_group_of_product(self):
        action = self.env.ref('equip3_construction_masterdata.action_view_group_of_product_menu_tree').read()[0]
        return action

    def button_uom(self):
        action = self.env.ref('uom.product_uom_form_action').read()[0]
        return action
    
    def button_pricelist(self):
        action = self.env.ref('product.product_pricelist_action2').read()[0]
        return action

    def button_tax(self):
        action = self.env.ref('account.action_tax_form').read()[0]
        return action
    
    def button_variable(self):
        action = self.env.ref('equip3_construction_masterdata.variable_estimation_action').read()[0]
        return action

    def button_job_subcon(self):
        action = self.env.ref('equip3_construction_masterdata.variable_subcon_action').read()[0]
        return action

    def button_estimate_template(self):
        action = self.env.ref('equip3_construction_sales_operation.action_job_estimate_template').read()[0]
        return action
    
    def button_penalty(self):
        action = self.env.ref('equip3_construction_masterdata.construction_penalty_view_action_id').read()[0]
        return action
    
    def button_job_matrix(self):
        action = self.env.ref('equip3_construction_sales_operation.action_approval_matrix_job_estimates').read()[0]
        return action
    
    def button_contract_matrix(self):
        action = self.env.ref('equip3_construction_sales_operation.action_approval_matrix_sale_order_const').read()[0]
        return action
    
    def button_overlimit_matrix(self):
        action = self.env.ref('equip3_sale_other_operation.action_limit_approval_matrix').read()[0]
        return action
    
    def button_job_estimate(self):
        action = self.env.ref('equip3_construction_reports.action_job_estimate_not_approved').read()[0]
        return action
    
    def button_job_estimate_approval(self):
        action = self.env.ref('equip3_construction_sales_operation.action_approval_matrix_job_estimates').read()[0]
        return action

    def button_job_estimate_approved(self):
        action = self.env.ref('equip3_construction_reports.action_job_estimate_approved').read()[0]
        return action
    
    def button_quotation(self):
        action = self.env.ref('equip3_construction_sales_operation.quotation_const_action').read()[0]
        return action
    
    def button_sale_order_approval(self):
        action = self.env.ref('equip3_construction_sales_operation.action_approval_matrix_sale_order_const').read()[0]
        return action

    def button_over_limit_approval(self):
        action = self.env.ref('equip3_sale_other_operation.action_limit_approval_matrix').read()[0]
        return action

    def button_sales_order(self):
        action = self.env.ref('equip3_construction_sales_operation.sale_order_const_action').read()[0]
        return action
    
    def button_cost_sheet(self):
        action = self.env.ref('equip3_construction_operation.action_view_job_cost_sheet_menu').read()[0]
        return action
    
    def button_project(self):
        action = self.env.ref('abs_construction_management.action_view_project').read()[0]
        return action

    def button_progressive_claim(self):
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action').read()[0]
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