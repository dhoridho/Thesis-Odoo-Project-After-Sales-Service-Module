from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    agriculture_daily_activity = fields.Boolean(related='company_id.agriculture_daily_activity', readonly=False)
    agriculture_daily_activity_wa_notif = fields.Boolean(related='company_id.agriculture_daily_activity_wa_notif', readonly=False)
    agriculture_monthly_planning = fields.Boolean(related='company_id.agriculture_monthly_planning', readonly=False)

    @api.onchange('agriculture_daily_activity')
    def _onchange_agriculture_daily_activity(self):
        if not self.agriculture_daily_activity:
            self.agriculture_daily_activity_wa_notif = False
    
    @api.onchange('agriculture')
    def _onchange_agriculture(self):
        if not self.agriculture:
            self.agriculture_monthly_planning = False
