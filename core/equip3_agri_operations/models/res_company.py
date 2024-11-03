from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    agriculture_daily_activity = fields.Boolean(string='Agriculture Plantation Plan')
    agriculture_daily_activity_wa_notif = fields.Boolean(string='Agriculture Plantation Plan WhatsApp Notification')
    agriculture_monthly_planning = fields.Boolean(string='Agriculture Monthly Planning', default=True)

    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        daily_activity_approval_matix_menu = self.env.ref('equip3_agri_operations.agriculture_settings_menu_approval_matrix_daily_activity')
        monthly_harvest_planning_menu = self.env.ref('equip3_agri_operations.menu_action_view_monthly_harvest_planning')
        
        daily_activity_approval_matix_menu.active = self.env.company.agriculture_daily_activity
        monthly_harvest_planning_menu.active = self.env.company.agriculture_monthly_planning
        return res
