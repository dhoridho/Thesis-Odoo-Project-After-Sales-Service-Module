from odoo import api, models, fields, _

class SaleFlowWizard(models.TransientModel):
    _name = 'sale.flow.wizard'
    _description = "Sale Flow Wizard"

    name = fields.Char(string='Name', default='Sales Flow')

    def button_customer(self):
        action = self.env.ref('account.res_partner_action_customer').read()[0]
        return action

    def button_pricelist(self):
        action = self.env.ref('product.product_pricelist_action2').read()[0]
        return action

    def button_add_product(self):
        action = self.env.ref('sale.product_template_action').read()[0]
        return action

    def button_one_time_set_up(self):
        pass
        
    def button_blanket_order(self):
        action = self.env.ref('blanket_sale_order_app.blanket_action_window').read()[0]
        return action

    def button_blanket_order_approval(self):
        action = self.env.ref('equip3_sale_operation.action_approval_matrix_sale_order').read()[0]
        return action

    def button_quotation(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').read()[0]
        return action

    def button_sale_order_approval(self):
        action = self.env.ref('equip3_sale_operation.action_approval_matrix_sale_order').read()[0]
        return action

    def button_over_limit_approval(self):
        action = self.env.ref('equip3_sale_other_operation.action_limit_approval_matrix').read()[0]
        return action

    def button_reporting(self):
        action = self.env.ref('sale.action_order_report_all').read()[0]
        return action
    
    def button_delivery_order(self):
        action = self.env.ref('equip3_inventory_operation.action_delivery_order').read()[0]
        return action
    
    def button_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        return action    

    def button_fee_head(self):
        action = self.env.ref('sale.action_orders').read()[0]
        return action