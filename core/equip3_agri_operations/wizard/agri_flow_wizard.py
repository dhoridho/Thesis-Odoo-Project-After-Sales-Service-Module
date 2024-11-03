from odoo import api, models, fields, _

class AgriFlowWizard(models.TransientModel):
    _name = 'agri.flow.wizard'
    
    name = fields.Char(string='Name', default='Agriculture Flow')

    def button_product(self):
        action = self.env.ref('product.product_template_action').read()[0]
        return action

    def button_activity(self):
        action = self.env.ref('equip3_agri_operations.action_crop_activity_config').read()[0]
        return action

    def button_worker(self):
        action = self.env.ref('equip3_agri_operations.action_view_agriculture_worker_group').read()[0]
        return action

    def button_estate(self):
        action = self.env.ref('equip3_agri_operations.action_crop_estate_config').read()[0]
        return action

    def button_division(self):
        action = self.env.ref('equip3_agri_operations.action_view_agriculture_division').read()[0]
        return action

    def button_block(self):
        action = self.env.ref('equip3_agri_operations.action_crop_block_config').read()[0]
        return action

    def button_budget_plan(self):
        action = self.env.ref('equip3_agri_operations.action_view_budget_planning_block').read()[0]
        return action

    def button_harvest_plan(self):
        action = self.env.ref('equip3_agri_operations.action_view_harvest_planning').read()[0]
        return action

    def button_daily_activity(self):
        action = self.env.ref('equip3_agri_operations.action_view_daily_activity').read()[0]
        return action

    def button_activity_line(self):
        action = self.env.ref('equip3_agri_operations.action_view_daily_activity_line').read()[0]
        return action

    def button_activity_record(self):
        action = self.env.ref('equip3_agri_operations.action_view_daily_activity_record').read()[0]
        return action

    def button_budget_analysis(self):
        action = self.env.ref('equip3_agri_operations.action_agriculture_budget_analysis_report').read()[0]
        return action

    def button_nursery_report(self):
        action = self.env.ref('equip3_agri_operations.action_agriculture_nursery_report').read()[0]
        return action

    def button_mature_cost(self):
        action = self.env.ref('equip3_agri_operations.action_agriculture_mature_cost_report').read()[0]
        return action

    def button_immature_cost(self):
        action = self.env.ref('equip3_agri_operations.action_agriculture_immature_cost_report').read()[0]
        return action

    def button_harvest_month(self):
        action = self.env.ref('equip3_agri_operations.action_agriculture_harvesting_monthly_report').read()[0]
        return action

    def button_harvest_analysis(self):
        action = self.env.ref('equip3_agri_operations.action_agriculture_harvesting_analysis_report').read()[0]
        return action