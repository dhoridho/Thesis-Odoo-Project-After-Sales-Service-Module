from odoo import api, models, fields, _


class CustomerProgressiveClaimFlowWizard(models.TransientModel):
    _name = 'customer.progressive.claim.flow.wizard'
    _description = 'Customer Progressive Claim Flow Wizard'

    name = fields.Char(string='Name', default='Customer Progressive Claim Flow')

    def button_customer(self):
        action = self.env.ref('account.res_partner_action_customer').read()[0]
        return action
    
    def button_chart_account(self):
        action = self.env.ref('account.action_account_form').read()[0]
        return action

    def button_fiscal_year(self):
        action = self.env.ref('sh_sync_fiscal_year.sh_fiscal_year_action').read()[0]
        return action
    
    def button_period(self):
        action = self.env.ref('sh_sync_fiscal_year.sh_fiscal_year_period_action').read()[0]
        return action

    def button_tax(self):
        action = self.env.ref('account.action_tax_form').read()[0]
        return action

    def button_claim_approval(self):
        action = self.env.ref('equip3_construction_accounting_operation.action_approval_matrix_claim_request').read()[0]
        return action

    def button_invoice_approval(self):
        action = self.env.ref('equip3_accounting_masterdata.action_approval_matrix_accounting_invoice').read()[0]
        return action

    def button_progressive_claim(self):
        action = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action').read()[0]
        return action

    def button_down_payment_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [
            ('move_type', '=', 'out_invoice'),
            ('project_invoice', '=', True),
            ('progressive_method', '=', 'down_payment')
            ]
        return action

    def button_claim_request(self):
        action = self.env.ref('equip3_construction_reports.customer_claim_request_action').read()[0]
        return action

    def button_progress_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [
            ('move_type', '=', 'out_invoice'),
            ('project_invoice', '=', True),
            ('progressive_method', '=', 'progress')
            ]
        return action

    def button_retention_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [
            ('move_type', '=', 'out_invoice'),
            ('project_invoice', '=', True),
            ('progressive_method', 'in', ['retention1', 'retention2'])
            ]
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
