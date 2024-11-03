from odoo import api, models, fields, _

class ManufWizard(models.TransientModel):
    _name = 'manuf.flow.wizard'
    _description = 'Manuf Flow Wizard'

    name = fields.Char(string='Name', default='Manufacturing Flow')

    def button_product(self):
        action = self.env.ref('mrp.product_template_action').read()[0]
        return action

    def button_bill_of_materials(self):
        action = self.env.ref('mrp.mrp_bom_form_action').read()[0]
        return action

    def button_work_center(self):
        action = self.env.ref('mrp.mrp_workcenter_action').read()[0]
        return action

    def button_work_center_group(self):
        action = self.env.ref('equip3_manuf_masterdata.action_view_mrp_workcenter_group').read()[0]
        return action
        
    def button_master_production_schedule(self):
        action = self.env.ref('equip3_manuf_reports.equip3_action_mrp_mps').read()[0]
        return action

    def button_manufacturing_plan(self):
        action = self.env.ref('equip3_manuf_operations.action_mrp_plan').read()[0]
        return action

    def button_manufacturing_order(self):
        action = self.env.ref('mrp.mrp_production_action').read()[0]
        return action

    def button_labour(self):
        action = self.env.ref('hr_holidays.hr_employee_action_from_department').read()[0]
        return action

    def button_labour_group(self):
        action = self.env.ref('equip3_manuf_masterdata.action_view_mrp_labor_group').read()[0]
        return action

    def button_work_orders(self):
        action = self.env.ref('mrp.mrp_workorder_todo').read()[0]
        return action
    
    def button_production_record(self):
        action = self.env.ref('equip3_manuf_operations_contd.action_mrp_consumption').read()[0]
        return action
    
    def button_unbuild_order(self):
        action = self.env.ref('mrp.mrp_unbuild').read()[0]
        return action    

    def button_rejected_goods_report(self):
        action = self.env.ref('equip3_manuf_reports.action_rejected_material_report').read()[0]
        return action

    def button_material_usage_report(self):
        action = self.env.ref('equip3_manuf_reports.action_material_usage_report').read()[0]
        return action

    def button_overal_equipment_effectiveness(self):
        action = self.env.ref('mrp.mrp_workcenter_productivity_report').read()[0]
        return action

    def button_finished_goods_report(self):
        action = self.env.ref('equip3_manuf_reports.action_finished_good_report').read()[0]
        return action