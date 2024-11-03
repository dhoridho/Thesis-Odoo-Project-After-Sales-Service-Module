# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from datetime import datetime
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError


class StockQuantInherited(models.Model):
    _inherit = 'stock.quant'

    expire_date = fields.Datetime(
        'Expiration_date', readonly=True, compute='_compute_lots_expire_date')
    stock_quant_sequence = fields.Char(string='No')
    analytic_account_group_ids = fields.Many2many(
        'account.analytic.tag', string="Analytic Groups")
    product_description = fields.Char(string="Description")
    initial_demand = fields.Float(string='Initial Demand')
    remaining = fields.Float(string="Remaining")
    quantity_done = fields.Float('Done', digits='Product Unit of Measure')
    fulfillment = fields.Float(string="Fulfillment (%)")
    filter_available_product_ids = fields.Many2many('product.product', 'product_id', 'avl_product_quant_rel',
                                                    'product_avl_product_quant_id', string="Available Product", compute='avl_qty_calculation', store=False)
    total_stock_in_package = fields.Float(string='Stock Danger')
    create_automatic = fields.Boolean(string="Create Automatic", store=True)
    
    # override this function cause cant inherit the function, to change some logic
    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        context = self._context
        if not context.get('picking_type_code') == 'outgoing':
            return super(StockQuantInherited, self)._update_reserved_quantity(product_id, location_id, quantity, lot_id, package_id, owner_id, strict)
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        reserved_quants = []
        
        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants
        
        quant_with_expire_date = sorted(quants.filtered(lambda q: q.expire_date), key=lambda x: (x.expire_date))
        quant_without_expire_date = sorted(quants.filtered(lambda q: not q.expire_date), key=lambda x: (x.expire_date))
        quants_combined = quant_with_expire_date + quant_without_expire_date
        
        for quant in quants_combined:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants

    # change default quantity on packages if create new line and fill description with product template id
    @api.onchange('location_id', 'product_id', 'lot_id', 'package_id', 'owner_id')
    def _onchange_location_or_product_id(self):
        res = super(StockQuantInherited,
                    self)._onchange_location_or_product_id()
        for record in self:
            record.quantity = 1
            record.product_description = record.product_id.product_tmpl_id.name
        return res

    @api.onchange('product_id')
    def _onchange_by_filter(self):
        for x in self:
            x.location_id = x.package_id.location_id_new.id

    @api.depends('package_id.packaging_id')
    def avl_qty_calculation(self):
        for record in self:
            product_in_packaging = self.env['product.packaging'].search(
                [('id', '=', record.package_id.packaging_id.id)])
            record.filter_available_product_ids = [
                (6, 0, product_in_packaging.product_id.ids)]

    @api.model
    def default_get(self, fields):
        res = super(StockQuantInherited, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'quant_ids' in context_keys:
                if len(self._context.get('quant_ids')) > 0:
                    next_sequence = len(self._context.get('quant_ids')) + 1
            res.update({'stock_quant_sequence': next_sequence})
        return res

    def _compute_lots_expire_date(self):
        for record in self:
            if record.lot_id.id == False:
                record.expire_date = False
            else:
                record.expire_date = record.lot_id.expiration_date

    @api.model
    def create_scrap(self):
        now = datetime.now()
        stock_quants = self.env['stock.quant'].search([])
        scrap_list = []
        ICP = self.env['ir.config_parameter'].sudo()
        expired_lot_serial_no = ICP.get_param(
            'expired_lot_serial_no', 'scrap_expire')
        is_auto_validate = ICP.get_param('is_auto_validate', False)
        quant_ids = []
        product_usage_quant = []
        context = dict(self.env.context) or {}
        for quant in stock_quants:
            if quant.location_id.usage == 'internal':
                if quant.expire_date == False:
                    continue
                if quant.lot_id.expiration_date < now:
                    if quant.quantity > 0:
                        if quant.location_id.is_expired_stock_location == False:
                            quant_ids.append(quant)
                        if expired_lot_serial_no == 'scrap_expire':
                            product_usage_quant.append(quant)
        if expired_lot_serial_no == 'scrap_expire':
            pu_temp_data = []
            final_data = []
            for rec in product_usage_quant:
                if {'location_id': rec.location_id.id, 'warehouse_id': rec.location_id.warehouse_id.id} in pu_temp_data:
                    filter_line = list(filter(lambda r: r.get('location_id').id == rec.location_id.id and r.get(
                        'warehouse_id').id == rec.location_id.warehouse_id.id, final_data))
                    if filter_line:
                        filter_line[0]['quants'].append(rec)
                else:
                    pu_temp_data.append(
                        {'location_id': rec.location_id.id, 'warehouse_id': rec.location_id.warehouse_id.id})
                    final_data.append({
                        'location_id': rec.location_id,
                        'warehouse_id': rec.location_id.warehouse_id,
                        'quants': [rec],
                    })
            scrap_type = self.env['usage.type'].search(
                [('name', '=', 'Auto Scrap')], limit=1)
            analytic_tags_ids = self.env['account.analytic.tag'].search(
                [('name', '=', 'Contracts')], limit=1)
            for data in final_data:
                if data.get('warehouse_id') and data.get('location_id'):
                    product_usage_line = [(0, 0, {'location_id': line.location_id.id,
                                                  'product_id': line.product_id.id,
                                                  'scrap_qty': line.available_quantity,
                                                  'product_uom_id': line.product_id.uom_id.id,
                                                  'lot_id': line.lot_id.id,
                                                  'package_id': line.package_id.id,
                                                  'owner_id': line.owner_id.id,
                                                  }) for line in data.get('quants')]
                    product_usage = self.env['stock.scrap.request'].create({
                        'scrap_request_name': 'Product Usage %s' % data.get('warehouse_id').name,
                        'warehouse_id': data.get('warehouse_id').id,
                        'scrap_type': scrap_type.id,
                        'analytic_tag_ids': [(6, 0, [analytic_tags_ids.id])],
                        'responsible_id': 1,
                        'create_uid': 1,
                        'scrap_ids': product_usage_line,
                        'is_product_usage': True,
                        'auto_scrap_notification': [(6, 0, data.get('warehouse_id').responsible_users.ids)]
                    })
                    # print('WAREHOUSE', data.get('warehouse_id').name, 'LOCATION', data.get('location_id').name, '| QUANT', len(data.get('quants')))
                    # product_usage.action_request_confirm()
                    # context.update({'auto_validate': True})
                    # product_usage.with_context(context).action_request_validated()
                    product_usage.with_context(
                        auto_validate=True).action_request_confirm()

        if expired_lot_serial_no == 'posted':
            temp_data = []
            final_data = []
            for rec in quant_ids:

                if {'location_id': rec.location_id.id, 'warehouse_id': rec.location_id.warehouse_id.id} in temp_data:
                    filter_line = list(filter(lambda r: r.get('location_id').id == rec.location_id.id and r.get(
                        'warehouse_id').id == rec.location_id.warehouse_id.id, final_data))
                    if filter_line:
                        filter_line[0]['quants'].append(rec)
                else:
                    temp_data.append(
                        {'location_id': rec.location_id.id, 'warehouse_id': rec.location_id.warehouse_id.id})
                    final_data.append({
                        'location_id': rec.location_id,
                        'warehouse_id': rec.location_id.warehouse_id,
                        'quants': [rec],
                    })
            for data in final_data:
                if data.get('location_id') and data.get('warehouse_id'):
                    source_location_id = data.get('location_id')
                    warehouse_id = source_location_id.warehouse_id
                    destination_location_id = self.env['stock.location'].search(
                        [('warehouse_id', '=', warehouse_id.id), ('is_expired_stock_location', '=', True)], limit=1)
                    operation_type_id = warehouse_id.int_type_id
                    schedule_date = datetime.today()
                    if destination_location_id and source_location_id:
                        internal_warehouse_id = self.env['stock.picking'].create({
                            'warehouse_id': warehouse_id.id,
                            'location_id': source_location_id.id,
                            'location_dest_id': destination_location_id.id,
                            'company_id': warehouse_id.company_id.id,
                            'scheduled_date': schedule_date,
                            'is_expired_tranfer': True,
                            'picking_type_id': operation_type_id.id,
                        })
                        for line in data.get('quants'):
                            move_line_id = self.env['stock.move'].create({
                                'name': line.product_id.display_name,
                                'product_id': line.product_id.id,
                                'product_uom_qty': line.available_quantity or 1,
                                'product_uom': line.product_id.uom_id.id,
                                'location_id': source_location_id.id,
                                'location_dest_id': destination_location_id.id,
                                'date': schedule_date,
                                'picking_id': internal_warehouse_id.id
                            })
                    else:
                        pass
                # internal_warehouse_id.action_confirm()
                # for line in internal_warehouse_id.move_ids_without_package:
                #     line.remaining = line.product_uom_qty
