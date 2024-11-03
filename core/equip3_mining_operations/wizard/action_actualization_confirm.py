from odoo import models, fields


class ActualizationConfirm(models.TransientModel):
    _name = 'action.actualization.confirm'
    _description = 'Actualization Confirm'

    mining_prod_act_id = fields.Many2one('mining.production.actualization', string='Actualization', required=True)
    message = fields.Char(string='Message', required=True, readonly=True)

    def action_continue(self):
        self.ensure_one()
        return self.mining_prod_act_id.action_confirm(skip_check=True)
