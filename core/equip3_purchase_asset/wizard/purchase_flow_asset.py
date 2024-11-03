from odoo import _, api, fields, models

class PurchaseFlowAsset(models.TransientModel):
    _name = 'purchase.flow.asset'
    _description = "Purchase Flow Asset"

    name = fields.Char(string='Name', default='Purchase Flow Assets Order')

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
        action = self.env.ref('equip3_purchase_asset.request_for_quotation_menu_order_action_assets').read()[0]
        return action
    
    def button_purchase_request(self):
        action = self.env.ref('equip3_purchase_asset.product_purchase_requests_assets').read()[0]
        return action
    
    def button_purchase_order(self):
        action = self.env.ref('equip3_purchase_asset.product_purchase_orders_assets').read()[0]
        return action
    
    def button_blanket_order(self):
        action = self.env.ref('equip3_purchase_asset.purchase_blanket_order_menu_order_action_assets').read()[0]
        return action
    
    def button_tender(self):
        action = self.env.ref('equip3_purchase_asset.sh_purchase_agreement_action_assets').read()[0]
        return action
    
    def button_direct_purchase(self):
        action = self.env.ref('equip3_purchase_asset.direct_purchase_menu_order_action_assets').read()[0]
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
    
    def button_create_assets(self):
        pass