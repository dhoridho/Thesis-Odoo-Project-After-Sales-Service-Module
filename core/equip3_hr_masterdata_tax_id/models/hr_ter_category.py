from odoo import fields, models, _
from odoo.exceptions import ValidationError


class HRTERCategory(models.Model):
    _name = 'hr.ter.category'
    _inherit = ['mail.thread']
    _description = 'HR TER Category'

    category = fields.Char('Category')
    ptkp_ids = fields.Many2many('hr.tax.ptkp', string="PTKP")
    bruto_income_from = fields.Float('Bruto Income From', group_operator=False)
    bruto_income_to = fields.Float('Bruto Income To', group_operator=False)
    ter_rate = fields.Float('Rate (%)', group_operator=False)

    def name_get(self):
        result = []
        for rec in self:
            name = rec.category + ' (' + str(rec.bruto_income_from) + ' - ' + str(rec.bruto_income_to)
            result.append((rec.id, name))
        return result