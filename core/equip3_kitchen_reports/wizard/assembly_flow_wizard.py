from odoo import api, fields, models


class AssemblyFlowWizard(models.TransientModel):
    _name = 'assembly.flow.wizard'
    
    name = fields.Char(string='Name', default='Assembly Flow')

    # def button_product(self):
    #     action = self.env.ref('product.product_template_action').read()[0]
    #     return action

    # def button_bill_of_materials(self):
    #     action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
    #     return action

    # def button_safety_stock_management(self):
    #     action = self.env.ref('equip3_kitchen_operations.action_view_safety_stock_management').read()[0]
    #     return action

    # def button_assembly(self):
    #     action = self.env.ref('equip3_kitchen_operations.action_view_dashboard_assemble').read()[0]
    #     return action

    # def button_assembly_production_record(self):
    #     action = self.env.ref('equip3_kitchen_operations.action_view_assemble_production_record').read()[0]
    #     return action

    # def button_disassembly(self):
    #     action = self.env.ref('equip3_kitchen_operations.action_view_dashboard_disassemble').read()[0]
    #     return action

    # def button_disassembly_production_record(self):
    #     action = self.env.ref('equip3_kitchen_operations.action_view_disassemble_production_record').read()[0]
    #     return action

    # def button_finished_product_report(self):
    #     action = self.env.ref('equip3_kitchen_reports.action_view_finished_product_assemble').read()[0]
    #     return action

    # def button_material_consumed(self):
    #     action = self.env.ref('equip3_kitchen_reports.action_view_material_consumed_assemble').read()[0]
    #     return action

