from odoo import api, models, fields, _

class PurchaseFlow(models.TransientModel):
    _name = 'purchase.flow'

    name = fields.Char(string='Name', default='Purchase Flow')

    def button_purchase_team(self):
        action = self.env.ref('dev_purchase_team.action_dev_purchase_team').read()[0]
        return action

    def button_vendor(self):
        action = self.env.ref('account.res_partner_action_supplier').read()[0]
        return action

    def button_vendor_pricelist(self):
        action = self.env.ref('product.product_supplierinfo_type_action').read()[0]
        return action

    def button_product(self):
        action = self.env.ref('purchase.product_normal_action_puchased').read()[0]
        return action

    def button_rfq(self):
        action = self.env.ref('purchase.purchase_rfq').read()[0]
        return action
    
    def button_purchase_request(self):
        action = self.env.ref('purchase_request.purchase_request_form_action').read()[0]
        return action
    
    def button_purchase_order(self):
        action = self.env.ref('purchase.purchase_form_action').read()[0]
        return action
    
    def button_blanket_order(self):
        action = self.env.ref('purchase_requisition.action_purchase_requisition').read()[0]
        return action
    
    def button_tender(self):
        action = self.env.ref('sh_po_tender_management.sh_purchase_agreement_action').read()[0]
        return action
    
    def button_direct_purchase(self):
        action = self.env.ref('equip3_purchase_other_operation_cont.action_direct_purchase').read()[0]
        return action
    
    def button_receiving_note(self):
        action = self.env.ref('equip3_inventory_operation.stock_picking_receiving_note').read()[0]
        return action
    
    def button_return(self):
        action = self.env.ref('dev_rma.action_dev_rma_rma').read()[0]
        return action
    
    def button_down_payment(self):
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        return action

    def button_vendor_bills(self):
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        return action
    
    def button_refund(self):
        action = self.env.ref('account.action_move_in_refund_type').read()[0]
        return action
    
    def button_payment(self):
        action = self.env.ref('account.action_account_payments_payable').read()[0]
        return action
    
    def button_report(self):
        action = self.env.ref('purchase.action_purchase_order_report_all').read()[0]
        return action