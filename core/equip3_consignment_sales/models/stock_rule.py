from odoo import _, api, fields, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        res = super(StockRule, self)._get_stock_move_values(
            product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if self._context.get('default_sale_consign'):
            partner_id = self.env['res.partner'].browse(res['partner_id'])
            consignment_location = partner_id.sale_consignment_location_id
            res['location_id'] = consignment_location.id

        return res
