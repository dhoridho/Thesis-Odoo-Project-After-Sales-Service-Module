
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HremployeeDisciplinaryInherit(models.Model):
    _inherit ='hr.employee'
    disciplinary_stage_ids = fields.Many2many('hr.employee.disciplinary',compute='_get_disciplinary_stage')


    @api.depends('name')
    def _get_disciplinary_stage(self):
        for res in self:
            if res.name:
                list_ids = []
                disclipnary = self.env['hr.employee.disciplinary'].search([('status','in',['confirmed','expired']),('employee_id','=',self.id)])
                if disclipnary:
                    data = [result.id for result in disclipnary]
                    list_ids.extend(data)
                    res.disciplinary_stage_ids = [(6,0,list_ids)]
                else:
                    res.disciplinary_stage_ids = False

            else:
                res.disciplinary_stage_ids = False

