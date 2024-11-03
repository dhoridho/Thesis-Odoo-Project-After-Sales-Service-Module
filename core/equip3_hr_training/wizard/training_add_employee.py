# -*- coding: utf-8 -*-

from odoo import fields, models, _


class EmployeeAddWizard(models.TransientModel):
    _name = "employee.add.wizard"
    _description = "Employee Selection Advanced Wizard"

    training_id = fields.Many2one('training.conduct')
    course_id = fields.Many2one('training.courses', string='Training Courses', related='training_id.course_id')
    training_histories_ids = fields.Many2many('training.histories', string='Training Histories', domain="[('course_ids', 'in', course_id), ('state', 'in', ['to_do', 'expired', 'failed'])]")

    def emp_add_select_btn(self):
        if(
                self and
                self.training_histories_ids
        ):
            for data in self:
                training_conduct_line_obj = self.env['training.conduct.line']
                for rec in data.training_histories_ids:
                    created_pol = training_conduct_line_obj.create({
                        'employee_id': rec.employee_id.id,
                        'conduct_id': data.training_id.id,
                    })

    def reset_list(self):
        if self:
            for rec in self:
                rec.training_histories_ids = None
                return {
                    'name': 'Select Employee',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'employee.add.wizard',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'res_id': rec.id,
                    'target': 'new',
                }