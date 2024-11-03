from odoo import api, models, fields, _

class KitchenFlowWizard(models.TransientModel):
    _name = 'kitchen.flow.wizard'
    
    name = fields.Char(string='Name', default='Kitchen Flow')

    def button_product(self):
        action = self.env.ref('product.product_template_action').read()[0]
        return action

    def button_bom(self):
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        return action
    
    def button_outlet(self):
        action = self.env.ref('equip3_kitchen_operations.action_view_outlet_order_two').read()[0]
        return action
    
    def button_cooking_list(self):
        action = self.env.ref('equip3_kitchen_operations.action_view_kitchen_cooking_list').read()[0]
        return action

    def button_dashboard(self):
        action = self.env.ref('equip3_kitchen_operations.action_view_dashboard_kitchen').read()[0]
        return action

    def button_safety_stock(self):
        action = self.env.ref('equip3_kitchen_operations.action_view_safety_stock_management').read()[0]
        return action
    
    def button_kitchen_product_record(self):
        action = self.env.ref('equip3_kitchen_operations.action_view_kitchen_production_record').read()[0]
        return action
    
    def button_finished_product_report(self):
        action = self.env.ref('equip3_kitchen_reports.action_view_finished_product_kitchen').read()[0]
        return action
    
    def button_material_consumed_report(self):
        action = self.env.ref('equip3_kitchen_reports.action_view_material_consumed_kitchen').read()[0]
        return action