# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrSptSequence(models.Model):
    _name = 'hr.spt.sequence'

    name = fields.Char('Year', required=True)
    number_next = fields.Integer(string='Next Number', required=True, default=1, help="Next number of this sequence")

    @api.constrains('name')
    def check_name(self):
        for record in self:
            if record.name:
                check_name = self.search([('name', '=', record.name), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("Year must be unique!")
