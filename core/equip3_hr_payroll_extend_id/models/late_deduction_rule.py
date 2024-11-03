# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LateDeductionRule(models.Model):
    _name = 'late.deduction.rule'
    _description = 'Late Deduction Rule'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    late_deduction_lines = fields.One2many('late.deduction.lines','deduction_rule_id')

    @api.constrains('name')
    def check_name(self):
        for record in self:
            if record.name:
                check_name = self.search([('name', '=', record.name), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("Name must be unique!")

class LateDeductionLines(models.Model):
    _name = 'late.deduction.lines'

    deduction_rule_id = fields.Many2one('late.deduction.rule')
    time = fields.Float(string='Time', required=True)
    amount = fields.Float(string='Amount', required=True)
    is_multiple = fields.Boolean('Is Multiple?')
    maximum_time = fields.Float('Maximum Time')

    @api.model
    def create(self, vals):
        if vals.get('deduction_rule_id'):
            if vals.get('is_multiple'):
                if vals.get('maximum_time') < vals.get('time'):
                    raise ValidationError("The Maximum time value must be greater than time value!")
        return super(LateDeductionLines, self).create(vals)

    def write(self, vals):
        res = super(LateDeductionLines, self).write(vals)
        for rec in self:
            if rec.is_multiple:
                if rec.maximum_time < rec.time:
                    raise ValidationError("The Maximum time value must be greater than time value!")
        return res

    @api.constrains('time')
    def check_time(self):
        for record in self:
            if record.time:
                check_time = self.search([('time', '=', record.time), ('id', '!=', record.id),
                                          ('deduction_rule_id', '=', record.deduction_rule_id.id)])
                if check_time:
                    raise ValidationError("Time must be different!")
