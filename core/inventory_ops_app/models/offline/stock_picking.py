# -*- coding: utf-8 -*-
from odoo import models, fields, tools
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from datetime import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _pre_action_done_hook(self):
        if self.env.context.get('process_from_app'):
            context = self._context.copy()  # self.env.context
            context.update({'skip_expired': True})
            self = self.with_context(context)
        return super(StockPicking, self)._pre_action_done_hook()

    def _check_immediate(self):
        immediate_pickings = self.browse()
        if self.env.context.get('process_from_app'):
            return immediate_pickings
        precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for picking in self:
            if all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in picking.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel'))):
                immediate_pickings |= picking
        return immediate_pickings

    # TODO: Mark AS todo button For App
    def app_action_confirm(self):
        self = self.with_context(process_from_app=False)
        error_message = 'success'
        try:
            # self._check_company()
            self.mapped('package_level_ids').filtered(lambda pl: pl.state == 'draft' and not pl.move_ids)._generate_moves()
            # call `_action_confirm` on every draft move
            self.mapped('move_lines').filtered(lambda move: move.state == 'draft')._app_action_confirm()
            # run scheduler for moves forecasted to not have enough in stock
            # self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done'))._trigger_scheduler()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        picking_data = self.app_stock_picking_retrive_data()
        return {'stock_picking_data': picking_data, 'error_message': error_message}

    # TODO: Validate button For App     
    # def app_button_validate(self, data_list):
    #     error_message = 'success'
    #     self = self.with_context(process_from_app=True)
    #     try:
    #         for item in data_list:
    #             move = self.env['stock.move'].browse(item.get('move_id'))
    #             move.quantity_done = item.get('qty')
    #         # self.app_end_scan(data_list)
    #         self.with_context(skip_immediate=True, skip_backorder=True).button_validate()
    #     except Exception as e:
    #         error_message = tools.ustr(e)
    #         self.env.cr.rollback()
    #     picking_data = self.app_stock_picking_retrive_data()
    #     for record in data_list:
    #         move_id = self.env['stock.move'].browse(record.get('move_id'))
    #         if move_id.product_id.tracking == "serial":
    #             self.env['stock.quant']._quant_tasks()
    #     return {'stock_picking_data': picking_data, 'error_message': error_message}
    
    # # TODO: Validate button For App
    def app_button_validate(self, data_list):
        error_message = 'success'
        self = self.with_context(process_from_app=True)
        try:
            move_lines = []
            for item in data_list:
                move = self.env['stock.move'].browse(item.get('move_id'))
                exp_date_str = item.get('exp_date')
                exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d %H:%M:%S') if exp_date_str else None
                
                if exp_date:
                    move.exp_date = exp_date

                product_tracking = move.product_id.tracking
                lot_serials = item.get('lot_serials', [])

                if product_tracking == 'serial':
                    if not lot_serials:
                        raise ValueError('Please provide serial numbers')
                    for serial in lot_serials:
                        move_lines.append({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'lot_name': serial.get('lot_sn'),
                            'qty_done': 1,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'picking_id': move.picking_id.id,
                        })
                elif product_tracking == 'lot':
                    if not lot_serials:
                        raise ValueError('Please provide lot numbers')
                    for lot in lot_serials:
                        move_lines.append({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'lot_name': lot.get('lot_sn'),
                            'qty_done': lot.get('lot_qty'),
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'picking_id': move.picking_id.id,
                        })
                else:
                    move.quantity_done = item.get('qty')

            if move_lines:
                self.env['stock.move.line'].create(move_lines)
            
            self.with_context(skip_immediate=True, skip_backorder=True).button_validate()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        picking_data = self.app_stock_picking_retrive_data()
        for record in data_list:
            move_id = self.env['stock.move'].browse(record.get('move_id'))
            if move_id.product_id.tracking in ['serial', 'lot']:
                self.env['stock.quant']._quant_tasks()
        return {'stock_picking_data': picking_data, 'error_message': error_message}

    # TODO: Endscan button For App
    def app_end_scan(self, data_list):
        error_message = 'success'
        try:
            self = self.with_context(process_from_app=True)
            self.ensure_one()
            self.do_unreserve()
            if self.picking_type_code == 'incoming':
                self.action_assign()
                for data in data_list:
                    move_id = self.env['stock.move'].browse(data['move_id'])
                    if move_id.product_id.tracking == 'none':
                        move_id.write({'quantity_done': data['qty']})
                    else:
                        move_id.move_line_nosuggest_ids.unlink()
                        for lot_dict in data['scanned_data']:
                            vals = {}
                            vals['picking_id'] = self.id
                            vals['product_id'] = move_id.product_id.id
                            vals['lot_name'] = lot_dict.get('lot_name', '')
                            vals['qty_done'] = lot_dict.get('qty')
                            vals['product_uom_id'] = move_id.product_uom.id
                            vals['location_id'] = move_id.location_id.id
                            vals['location_dest_id'] = move_id.location_dest_id.id
                            res = self.env['stock.move.line'].create(vals)
                        move_id.write({'quantity_done': data.get('qty', 0), 'picking_type_id': self.picking_type_id.id})
            else:
                data_list = filter(lambda x: x.get('qty') > 0, data_list)
                self.with_context(picking_reserve=data_list).action_assign()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        picking_data = self.app_stock_picking_retrive_data()
        return {'error_message': error_message, 'stock_picking_data': picking_data}

    def get_offline_unreserved_quants(self, move_id):
        if not self:
            return []
        if type(move_id) == int:
            move_id = self.env['stock.move'].browse(move_id)
        self.ensure_one()
        quants_dict = {}
        quants = self.env['stock.quant'].search(
            [('location_id', '=', move_id.location_id.id), ('product_id', '=', move_id.product_id.id),
             ('lot_id', '!=', False)])
        for quant in quants:
            lot_id = quant.lot_id
            if lot_id.id in quants_dict:
                quants_dict[lot_id.id]['qty'] += quant.available_quantity
            else:
                vals = {}
                vals['lot_name'] = lot_id.name
                vals['lot_id'] = lot_id.id
                vals['qty'] = quant.available_quantity
                vals['scanned_qty'] = 0.0
                # if quant.available_quantity > 0:
                quants_dict[lot_id.id] = vals
        for move_line in move_id.move_line_ids.filtered(lambda l: l.lot_id):
            lot_id = move_line.lot_id
            if lot_id.id in quants_dict:
                quants_dict[lot_id.id]['scanned_qty'] += move_line.product_uom_qty
                quants_dict[lot_id.id]['qty'] += move_line.product_uom_qty
            else:
                quant_vals = {}
                quant_vals['lot_name'] = lot_id.name
                quant_vals['lot_id'] = lot_id.id
                quant_vals['qty'] = move_line.product_uom_qty
                quant_vals['scanned_qty'] = move_line.product_uom_qty
                quants_dict[lot_id.id] = quant_vals
        quant_list = []
        for key in quants_dict.keys():
            quant_list.append(quants_dict[key])
        return quant_list
