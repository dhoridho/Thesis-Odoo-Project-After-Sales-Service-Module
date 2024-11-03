from odoo import api, fields, models


class MiningModuleFlow(models.TransientModel):
    _name = 'mining.module.flow'
    _rec_name = 'name'

    name = fields.Char(string='Name', default='Module Flow')

    def action_menu_product(self):
        return self.env.ref('equip3_mining_operations.product_master_data_mining_action_id').read()[0]
    
    def action_menu_operations(self):
        return self.env.ref('equip3_mining_operations.mining_operations_two_action').read()[0]
    
    def action_menu_worker_group(self):
        return self.env.ref('equip3_mining_operations.mining_worker_group_action').read()[0]
    
    def action_menu_mining_site(self):
        return self.env.ref('equip3_mining_operations.mining_site_control_actions').read()[0]
    
    def action_menu_mining_pit(self):
        return self.env.ref('equip3_mining_operations.action_mining_project_control').read()[0]
    
    def action_menu_planning(self):
        return self.env.ref('equip3_mining_operations.action_view_mining_plan').read()[0]
    
    def action_menu_production_plan(self):
        return self.env.ref('equip3_mining_operations.mining_production_plan_action').read()[0]
    
    def action_menu_production_lines(self):
        return self.env.ref('equip3_mining_operations.mining_production_line_action').read()[0]
    
    def action_menu_actualization(self):
        return self.env.ref('equip3_mining_operations.mining_production_act_action').read()[0]
    
    def action_menu_fuel_logs(self):
        return self.env.ref('equip3_asset_fms_masterdata.maintenance_fuel_logs_action').read()[0]
    
    def action_menu_production_report(self):
        return self.env.ref('equip3_mining_reports.action_mining_production_report').read()[0]
    
    def action_menu_asset_production_report(self):
        return self.env.ref('equip3_mining_reports.action_mining_asset_report').read()[0]
    
    def action_menu_stripping_ratio_report(self):
        return self.env.ref('equip3_mining_reports.action_view_stripping_ratio_report').read()[0]
    
    def action_menu_fuel_ratio_report(self):
        return self.env.ref('equip3_mining_reports.action_view_fuel_ratio_report').read()[0]
    
    def arrow(self):
        return True