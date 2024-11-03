# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrGoalTypes(models.Model):
    _name = 'hr.goal.types'
    _description = 'HR Goal Types'

    def _get_appraisal_group_domain(self):
        return [('category_id','=',self.env.ref('equip3_hr_employee_appraisals.module_category_appraisal').id)]

    name = fields.Char('Goal Types')
    group_ids = fields.Many2many('res.groups', string='Group', domain=_get_appraisal_group_domain)

    def unlink(self):
        for data in self:
            raise UserError(("You cannott delete Goal Types."))
        return super(HrGoalTypes, self).unlink()
    
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a Goal Type.'))