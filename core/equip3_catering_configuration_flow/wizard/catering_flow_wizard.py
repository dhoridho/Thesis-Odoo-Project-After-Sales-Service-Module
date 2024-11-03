from odoo import api, models, fields, _

class CateringFlowWizard(models.TransientModel):
    _name = 'catering.flow.wizard'

    name = fields.Char(string='Name', default='Catering Flow')

    def button_catering_order(self):
        action = self.env.ref('equip3_catering_operation.action_catering_order').read()[0]
        return action

    def button_menu_planner(self):
        action = self.env.ref('equip3_catering_masterdata.catering_menu_planner_action').read()[0]
        return action

    def button_delivery(self):
        action = self.env.ref('equip3_inventory_operation.action_delivery_order').read()[0]
        return action

    def button_reporting(self):
        action = self.env.ref('equip3_catering_report.action_catering_pivot_analysis').read()[0]
        return action
        
    def button_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        return action

    def button_customers(self):
        action = self.env.ref('base.action_partner_customer_form').read()[0]
        return action

    def button_products(self):
        action = self.env.ref('equip3_catering_masterdata.product_template_action_product').read()[0]
        return action

    def button_fee_head(self):
        action = self.env.ref('equip3_catering_configuration_flow.catering_flow_wizard_action').read()[0]
        return action