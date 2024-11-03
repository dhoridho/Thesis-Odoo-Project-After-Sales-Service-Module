from odoo import api, models, fields, _

class MaterialPurchaseFlowWizard(models.TransientModel):
    _name = 'material.purchase.flow.wizard'

    name = fields.Char(string='Name', default='Material Purchase Flow')

    def button_vendor(self):
        action = self.env.ref('account.res_partner_action_supplier').read()[0]
        return action

    def button_vendor_pricelist(self):
        action = self.env.ref('product.product_supplierinfo_type_action').read()[0]
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
    
    def button_variable(self):
        action = self.env.ref('equip3_construction_masterdata.variable_estimation_action').read()[0]
        return action

    def button_cost_sheet(self):
        action = self.env.ref('equip3_construction_operation.action_view_job_cost_sheet_menu').read()[0]
        return action

    def button_project_budget(self):
        action = self.env.ref('equip3_construction_operation.project_budget_action').read()[0]
        return action

    def button_material_request(self):
        action = self.env.ref('equip3_construction_purchase_operation.purchase_orders_material_request_action').read()[0]
        return action
    
    def button_purchase_request(self):
        action = self.env.ref('equip3_construction_purchase_operation.purchase_request_menu_order_action').read()[0]
        return action

    def button_interwarehouse_transfer(self):
        action = self.env.ref('equip3_inventory_operation.action_internal_transfer_request').read()[0]
        return action

    def button_intrawarehouse_transfer(self):
        action = self.env.ref('equip3_inventory_operation.action_interwarehouse_transfer').read()[0]
        return action
    
    def button_purchase_tender(self):
        action = self.env.ref('equip3_construction_purchase_other_operation.purchase_tender_menu_order_action').read()[0]
        return action

    def button_request_for_quotation(self):
        action = self.env.ref('equip3_construction_purchase_operation.request_for_quotation_menu_order_action').read()[0]
        return action

    def button_purchase_order(self):
        action = self.env.ref('equip3_construction_purchase_operation.purchase_orders_menu_order_action').read()[0]
        return action

    def button_bill(self):
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
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