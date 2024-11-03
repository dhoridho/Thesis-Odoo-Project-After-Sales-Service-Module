from odoo import api, models, fields, _

class CRMFlowWizard(models.TransientModel):
    _name = 'crm.flow.wizard'
    _description = 'CRM Flow Wizard'

    name = fields.Char(string='Name', default='CRM Configuration Flow')

    def button_follow_ups_type(self):
        action = self.env.ref('sales_team.mail_activity_type_action_config_sales').read()[0]
        return action

    def button_meetings_type(self):
        action = self.env.ref('calendar.action_calendar_event_type').read()[0]
        return action   

    def button_leads_type(self):
        action = self.env.ref('equip3_crm_operation.action_crm_lead_type').read()[0]
        return action

    def button_sales_teams(self):
        action = self.env.ref('sales_team.sales_team_config_action').read()[0]
        return action  

    def button_stages(self):
        action = self.env.ref('crm.crm_stage_action').read()[0]
        return action

    def button_tags(self):
        action = self.env.ref('sales_team.sales_team_crm_tag_action').read()[0]
        return action  

    def button_lost_reasons(self):
        action = self.env.ref('crm.crm_lost_reason_action').read()[0]
        return action  

    def button_leads(self):
        action = self.env.ref('crm.crm_lead_action_pipeline').read()[0]
        return action

    def button_follow_ups(self):
        action = self.env.ref('crm.crm_lead_action_my_activities').read()[0]
        return action

    def button_quotations(self):
        action = self.env.ref('sale.action_quotations').read()[0]
        return action

    def button_meeting(self):
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        return action

    def button_sales_orders(self):
        action = self.env.ref('equip3_crm_operation.action_orders_crm').read()[0]
        return action

    def button_reporting(self):
        action = self.env.ref('equip3_crm_report.action_lead_pivot_analysis').read()[0]
        return action