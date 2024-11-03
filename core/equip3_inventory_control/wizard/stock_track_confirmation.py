from odoo import fields, models, fields, api, _


class StockTrackConfirmation(models.TransientModel):
    _inherit = 'stock.track.confirmation'

    def action_confirm(self):
        confirmed_inventories = self.filtered(lambda o: o.inventory_id.state == 'confirm')
        for confirmation in confirmed_inventories:
            confirmation.inventory_id.with_context(skip_check_tracked_lines=True).action_complete()
        return super(StockTrackConfirmation, self - confirmed_inventories).action_confirm()
