from odoo import api, fields, models, _


class HrEmployeeSkill(models.Model):
    _inherit = 'hr.employee.skill'
    
    @api.model
    def _domain_skill(self):
        return [('company_id','=',self.env.company.id)]
    
    skill_type_id = fields.Many2one('hr.skill.type',domain=_domain_skill)