from datetime import datetime
from odoo import api, fields,models
from odoo.exceptions import ValidationError


class equip3ManPowerPlanningPeriod(models.Model):
    _name = "manpower.planning.period"
    _inherit = ['mail.thread','mail.activity.mixin']
    
    name = fields.Char(compute='_compute_name',store=True)
    mpp_year = fields.Many2one('hr.years',"Year")
    mpp_type = fields.Many2one('manpower.planning.type',"MPP Type")
    start_period = fields.Date()
    end_period = fields.Date()
    
    @api.constrains('start_period','end_period','mpp_year')
    def _constrain_start_period_end_period(self):
        for data in self:
            start_period=datetime.strptime(str(data.start_period),"%Y-%m-%d")
            end_period=datetime.strptime(str(data.end_period),"%Y-%m-%d")
            if start_period.year != data.mpp_year.name or end_period.year != data.mpp_year.name:
                raise ValidationError("Year must be same with period years !")
            
    
    
    
    @api.depends('start_period','end_period')
    def _compute_name(self):
        for data in self:
            if data.start_period and data.end_period:
                start_period=datetime.strptime(str(data.start_period),"%Y-%m-%d")
                end_period=datetime.strptime(str(data.end_period),"%Y-%m-%d")
                start_period_string=datetime(start_period.year,start_period.month,start_period.day)
                end_period_string=datetime(end_period.year,end_period.month,end_period.day)
                data.name = f"{start_period_string.strftime('%d %b %Y')} - {end_period_string.strftime('%d %b %Y')}"
            else:
                data.name = ''
                
    

    
    
    