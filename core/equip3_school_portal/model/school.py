from odoo import api, fields, models


class EmsSubject(models.Model):
    _inherit = "subject.weightage"

    presence_value = fields.Integer(string='Presence Percentage', compute='_compute_presence_value')

    @api.depends('presence_persentage')
    def _compute_presence_value(self):
        for record in self:
            if record.presence_persentage:
                record.presence_value = record.presence_persentage * 100
            else:
                record.presence_value = 0
