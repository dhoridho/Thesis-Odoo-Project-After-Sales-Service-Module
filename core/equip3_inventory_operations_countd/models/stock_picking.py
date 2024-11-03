from odoo import _, api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_without_quantities_error_message(self):
        """ Returns the error message raised in validation if no quantities are reserved or done.
        The purpose of this method is to be overridden in case we want to adapt this message.

        :return: Translated error message
        :rtype: str
        """
        return _(
            'You cannot validate a transfer if no quantities are reserved nor done.'
            # 'To force the transfer, click Force Validate or switch in edit mode and encode the done quantities.'
        )

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for rec in self:
            if rec.picking_batch_id:
                rec.picking_batch_id.product_by_same_locations()
        return res
