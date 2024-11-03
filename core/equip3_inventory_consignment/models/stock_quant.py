from odoo import models, fields, api, _

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_consignment = fields.Boolean('Is Consignment')
    consignment_id = fields.Many2one('consignment.agreement')

    @api.model
    def create(self, vals):
        res = super(StockQuant,self).create(vals)
        context = self._context
        if context.get('default_is_consignment'):
            res.write({'is_consignment' : True})
        return res


    @api.model
    def _unlink_zero_quants(self):
        """ _update_available_quantity may leave quants with no
        quantity and no reserved_quantity. It used to directly unlink
        these zero quants but this proved to hurt the performance as
        this method is often called in batch and each unlink invalidate
        the cache. We defer the calls to unlink in this method.
        """
        precision_digits = max(6, self.sudo().env.ref('product.decimal_product_uom').digits * 2)
        # Use a select instead of ORM search for UoM robustness.
        query = """ SELECT
                        id
                    FROM
                        stock_quant
                    WHERE
                            (round(quantity::numeric, %s) = 0 OR quantity IS NULL) AND round(reserved_quantity::numeric, %s) = 0 AND is_consignment = False;"""
        params = (precision_digits, precision_digits)
        self.env.cr.execute(query, params)
        quant_ids = self.env['stock.quant'].browse([quant['id'] for quant in self.env.cr.dictfetchall()])
        quant_ids.sudo().unlink()
