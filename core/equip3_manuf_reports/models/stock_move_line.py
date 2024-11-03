from odoo import models, fields, api
from odoo.tools import float_is_zero


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    api.depends(
        'company_id', 'product_id', 'picking_id', 'production_id', 'production_id.is_subcontracted',
        'location_dest_id', 'lot_id', 'package_id', 'owner_id')
    def _compute_subcon_values(self):

        Quant = self.env['stock.quant']
        Purchase = self.env['purchase.order']
        for record in self:
            product_id = record.product_id

            record.subcon_qty_available = 0.0
            if product_id:
                record.subcon_qty_available = Quant._get_available_quantity(
                    product_id, 
                    record.location_dest_id, 
                    lot_id=record.lot_id, 
                    package_id=record.package_id, 
                    owner_id=record.owner_id
                )

            record.subcon_partner_id = False
            if record.production_id and record.production_id.is_subcontracted:
                purchase_id = Purchase.search([('subcon_production_id', '=', record.production_id.id)], limit=1)
                record.subcon_partner_id = purchase_id.partner_id.id

            location_id = record.location_dest_id
            if not location_id:
                record.subcon_svl_value = 0.0
                continue

            company_id = record.company_id
            owner_id = record.owner_id
            if not location_id._should_be_valued() or (owner_id and owner_id != company_id.partner_id):
                record.subcon_svl_value = 0.0
                continue

            if product_id.cost_method == 'fifo':
                quantity = product_id.quantity_svl
                if float_is_zero(quantity, precision_rounding=product_id.uom_id.rounding):
                    record.subcon_svl_value = 0.0
                    continue
                average_cost = product_id.with_company(company_id).value_svl / quantity
                record.subcon_svl_value = record.qty_done * average_cost
            else:
                record.subcon_svl_value = record.qty_done * product_id.with_company(company_id).standard_price

    subcon_partner_id = fields.Many2one('res.partner', compute=_compute_subcon_values, store=True)
    subcon_qty_available = fields.Float(digits='Product Unit of Measure', compute=_compute_subcon_values, store=True)
    subcon_svl_value = fields.Float(digits='Product Unit of Measure', compute=_compute_subcon_values, store=True)
