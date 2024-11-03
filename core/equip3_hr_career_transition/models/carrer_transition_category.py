from odoo import models,fields


class Equip3CareerTransationCategory(models.Model):
    _name = "career.transition.category"
    _description="Career Transition Category"
    
    def _get_transition_domain(self):
        return [('category_id','=',self.env.ref('equip3_hr_career_transition.career_transition_category').id)] 
    
    _order ='create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char()
    group_ids = fields.Many2many('res.groups',domain=_get_transition_domain)
    