from odoo import api, models,fields
from datetime import datetime



class Equip3CareerHrContract(models.Model):
    _inherit = 'hr.contract'
    career_transition_id = fields.Many2one('hr.career.transition')
    
    
    @api.model
    def create(self, vals_list):
        res =  super(Equip3CareerHrContract,self).create(vals_list)
        if res.career_transition_id:
            if res.career_transition_id.contract_id.date_end <= datetime.now().date():
                res.career_transition_id.contract_id.state = 'close'
            res.career_transition_id.is_hide_renew = True
        return res
    
    