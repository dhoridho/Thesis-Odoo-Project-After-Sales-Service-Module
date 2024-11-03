from odoo import fields, models


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def action_reset_sequence(self):
        for sequence in self:
            sequence.number_next_actual = 1
            sequence.number_next = 1
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }