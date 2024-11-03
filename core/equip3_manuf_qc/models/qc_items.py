from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ChecksheetDimensions(models.Model):
    _name = 'qc.checksheet.items'
    _description = 'Checksheet Items'

    name = fields.Char('Item')
    direction = fields.Char('Direction')
    answer_ids = fields.One2many('qc.checksheet.answer', 'item_id', string="Answer")


    @api.constrains('answer_ids')
    def _check_answer(self):
        for record in self:
            if not record.answer_ids:
                raise ValidationError(_('Answers Must Be Required!'))
            return True
