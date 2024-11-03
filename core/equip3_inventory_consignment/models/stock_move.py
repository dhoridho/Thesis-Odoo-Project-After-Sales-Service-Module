from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_common_svl_vals(self):
        res = super(StockMove, self)._prepare_common_svl_vals()
        """ Receiving Notes consignment fields.
        For Delivery Order, see _prepare_out_svl_vals """
        if self._is_in():
            consignment_id = self.picking_id.consignment_id.id
            is_consignment = consignment_id is not False
            res.update({
                'is_consignment': consignment_id is not False,
                'consignment_id': consignment_id
            })
        return res
