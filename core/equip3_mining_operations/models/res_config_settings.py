from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    overburden = fields.Boolean(string='Overburden', related='company_id.overburden', readonly=False)
    coal_getting = fields.Boolean(string='Coal Getting', related='company_id.coal_getting', readonly=False)
    hauling = fields.Boolean(string='Hauling', related='company_id.hauling', readonly=False)
    crushing = fields.Boolean(string='Crushing', related='company_id.crushing', readonly=False)
    barging = fields.Boolean(string='Barging', related='company_id.barging', readonly=False)
    overburden_uom = fields.Many2one(related='company_id.overburden_uom', readonly=False, string="Unit of Measure")
    coal_getting_uom = fields.Many2one(related='company_id.coal_getting_uom', readonly=False, string="Unit of Measure")
    hauling_uom = fields.Many2one(related='company_id.hauling_uom', readonly=False, string="Unit of Measure")
    crushing_uom = fields.Many2one(related='company_id.crushing_uom', readonly=False, string="Unit of Measure")
    barging_uom = fields.Many2one(related='company_id.barging_uom', readonly=False, string="Unit of Measure")
    
    # approval matrix
    mining_site = fields.Boolean(related='company_id.mining_site', readonly=False, string='Mining Site')
    mining_project = fields.Boolean(related='company_id.mining_project', readonly=False, string='Mining Pit')
    daily_production = fields.Boolean(related='company_id.daily_production', readonly=False, string='Daily Production')
    
    mining_production_plan = fields.Boolean(related='company_id.mining_production_plan', readonly=False, string='Mining Production Plan')
    mining_production_line = fields.Boolean(related='company_id.mining_production_line', readonly=False, string='Mining Production Line')
    mining_production_act = fields.Boolean(related='company_id.mining_production_act', readonly=False, string='Mining Production Actualization')

    mining_site_wa_notif = fields.Boolean(related='company_id.mining_site_wa_notif', readonly=False)
    mining_project_wa_notif = fields.Boolean(related='company_id.mining_project_wa_notif', readonly=False)
    daily_production_wa_notif = fields.Boolean(related='company_id.daily_production_wa_notif', readonly=False)
    
    mining_production_plan_wa_notif = fields.Boolean(related='company_id.mining_production_plan_wa_notif', readonly=False)
    mining_production_line_wa_notif = fields.Boolean(related='company_id.mining_production_line_wa_notif', readonly=False)
    mining_production_act_wa_notif = fields.Boolean(related='company_id.mining_production_act_wa_notif', readonly=False)

    @api.onchange('mining_site')
    def _onchange_mining_site(self):
        if not self.mining_site:
            self.mining_site_wa_notif = False

    @api.onchange('mining_project')
    def _onchange_mining_project(self):
        if not self.mining_project:
            self.mining_project_wa_notif = False

    @api.onchange('daily_production')
    def _onchange_daily_production(self):
        if not self.daily_production:
            self.daily_production_wa_notif = False
            
    @api.onchange('mining_production_plan')
    def _onchange_mining_production_plan(self):
        if not self.mining_production_plan:
            self.mining_production_plan_wa_notif = False
            
    @api.onchange('mining_production_line')
    def _onchange_mining_production_line(self):
        if not self.mining_production_line:
            self.mining_production_line_wa_notif = False

    @api.onchange('mining_production_act')
    def _onchange_mining_production_act(self):
        if not self.mining_production_act:
            self.mining_production_act_wa_notif = False
    
