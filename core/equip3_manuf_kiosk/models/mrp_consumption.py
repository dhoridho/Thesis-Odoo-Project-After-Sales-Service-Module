from odoo import models, fields


class MrpConsumption(models.Model):
    _inherit = 'mrp.consumption'

    def _action_confirm(self):
        result = super(MrpConsumption, self)._action_confirm()
        self.move_raw_ids.write({'kiosk_qty': 0.0})
        return result
