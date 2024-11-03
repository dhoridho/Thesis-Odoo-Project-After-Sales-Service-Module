from odoo import models,fields


class Equip3CareerTransationType(models.Model):
    _name = "career.transition.type"
    _description="Career Transition Type"
    _order ='create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    def _get_transition_domain(self):
        return [('category_id','=',self.env.ref('equip3_hr_career_transition.career_transition_category').id)]
    
    name = fields.Char()
    letter_id = fields.Many2one('hr.career.transition.letter')
    career_transition_category_id = fields.Many2one('career.transition.category')
    group_ids = fields.Many2many('res.groups',domain=_get_transition_domain)
    encashment_leave = fields.Boolean(string='Leave Encashment', default=False)
    leave_type_ids = fields.Many2many('hr.leave.type', string='Leave Type')
    notice_period = fields.Boolean(string='Notice Period', default=False)
    notice_period_days = fields.Integer(string='Notice Period Days')
    day_count_by = fields.Selection(
        [('work_day', 'Work Day'),
         ('calendar_day', 'Calendar Day')], default="calendar_day", string="Day Count By")