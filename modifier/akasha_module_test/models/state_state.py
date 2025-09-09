from odoo import models, fields, api
from odoo.exceptions import UserError

class StateState(models.Model):
    _name = "state.state"

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence')
    main_model_ids = fields.One2many('main.model', 'state_id', 'Main Models', readonly=True)

    @api.constrains('sequence')
    def _check_sequence_uniq(self):
        for state in self:
            if state.sequence:
                state_ids = self.search([('sequence', '=', state.sequence)])
                if len(state_ids) > 1:
                    raise UserError(f"Sequence {state.sequence} is not unique.")

    # def create(self, vals):
    #     sequence = self.search([])
    #     if vals.get('sequence') in :
    #
    #     res = super().create(vals)
    #     return res

