from odoo import _, api, fields, models
import json


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        res = super(StockMove, self)._get_new_picking_values()
        if self._context.get('default_sale_consign') or self._context.get('active_model') == 'sale.consignment.agreement':
            partner_id = self.env['res.partner'].browse(res['partner_id'])
            consignment_location = partner_id.sale_consignment_location_id
            picking_type_id = self.env['stock.picking.type'].search([
                ('default_location_src_id', '=', consignment_location.id),
                ('code', '=', 'outgoing'),
                ('warehouse_id', '=', consignment_location.warehouse_id.id)], limit=1)
            res.update({'location_id': consignment_location.id,
                       'picking_type_id': picking_type_id.id})
            self.location_id = consignment_location.id
        return res

    product_consignment_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    product_consignment_id_domain = fields.Char(
        string="Product Domain", compute='_compute_product_consignment_id')

    @api.depends('product_consignment_id', 'picking_id.sale_consignment_id')
    def _compute_product_consignment_id(self):
        if self.picking_id.sale_consignment_id:
            product_ids = self.picking_id.transfer_id.product_line_ids.mapped(
                'product_id')
            existing_product_ids = self.picking_id.move_ids_without_package.mapped(
                'product_id').ids
            new_product_ids = [
                product_id.id for product_id in product_ids if product_id.id not in existing_product_ids]
            domain = json.dumps([('id', 'in', new_product_ids)])
            self.product_consignment_id_domain = domain
        else:
            self.product_consignment_id_domain = False

    @api.onchange('product_consignment_id')
    def onchange_product_id_consignment(self):
        if self.product_consignment_id:
            self.product_id = self.product_consignment_id
            self.product_description = self.product_consignment_id.display_name
