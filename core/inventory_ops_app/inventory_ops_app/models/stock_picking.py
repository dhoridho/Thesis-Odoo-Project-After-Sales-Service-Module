# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime
from odoo import tools

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def app_custom_button(self):
        button_list = []
        if self.picking_type_code == 'incoming':
            if self.state == 'draft': # Draft
                button_list.append({'button_name': 'MARK AS TODO', 'button_method': 'button_mark_as_todo'})
            elif self.state == 'assigned': # Ready
                button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate'})
            elif self.state == 'confirmed': # Waiting
                button_list.append({'button_name': 'CHECK AVAILABILITY', 'button_method': 'button_check_availability'})
                button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate'})
        if self.picking_type_code == 'outgoing':
            if self.state == 'draft':
                button_list.append({'button_name': 'MARK AS TODO', 'button_method': 'button_mark_as_todo'})
            elif self.state == 'assigned':
                button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate'})
                button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve'})
            elif self.state == 'confirmed':
                button_list.append({'button_name': 'CHECK AVAILABILITY', 'button_method': 'button_check_availability'})
                button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate'})
                button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve'})
        if self.picking_type_code == 'internal':
            if self.state == 'draft':
                button_list.append({'button_name': 'MARK AS TODO', 'button_method': 'button_mark_as_todo'})
            elif self.state == 'assigned':
                button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate'})
                button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve'})
            elif self.state == 'confirmed':
                button_list.append({'button_name': 'CHECK AVAILABILITY', 'button_method': 'button_check_availability'})
                button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate'})
                button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve'})
        return button_list

    def button_mark_as_todo(self):
        error_message = 'success'
        try:
            self.action_confirm()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    def button_check_availability(self):
        error_message = 'success'
        try:
            self.action_assign()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    def button_unreserve(self):
        error_message = 'success'
        try:
            self.do_unreserve()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    # List View - Receiving, Picking and Internal Transfer
    def get_picking_list(self, wh_id, picking_type_code, filter, sort='id asc', start_date=False, end_date=False):
        data_list = []
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved','waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        domain = [('picking_type_id.warehouse_id', '=', wh_id), ('picking_type_code', '=', picking_type_code)]
        if filter == 'late':
            domain.append(('state', 'in', ('assigned', 'waiting', 'confirmed')))
            domain.append(('scheduled_date', '<', str(datetime.now())[:19]))
        elif filter == 'ready':
            domain.append(('state', '=', 'assigned'))
        elif filter == 'waiting':
            domain.append(('state', 'in', ('confirmed', 'waiting')))
        elif filter == 'draft':
            domain.append(('state', '=', 'draft'))
        elif filter == 'backorders':
            domain.append(('state', 'in', ('confirmed', 'assigned', 'waiting')))
            domain.append(('backorder_id', '!=', False))
        elif filter == 'done':
            domain.append(('state', '=', 'done'))
            domain.append(('scheduled_date', '>=', start_date))
            domain.append(('scheduled_date', '<=', end_date))
        elif filter == 'receiving_notes':
            domain = [('picking_type_code', '=', 'incoming'),('is_expired_tranfer', '=', False), ('state', "not in", ('done', 'cancel','rejected'))]
        elif filter == 'delivery_orders':
            domain = [('picking_type_code', '=', 'outgoing'),('is_expired_tranfer', '=', False), ('state', "not in", ('done', 'cancel'))]
        elif filter == 'intrawarehouse_transfer':
            domain = [('is_interwarehouse_transfer', '=', True), ('state', "not in", ('done', 'cancel'))]
        elif filter == 'receiving_notes_done':
            domain = [('picking_type_code', '=', 'incoming'), ('is_expired_tranfer', '=', False), ('state', '=', 'done'), ('scheduled_date', '>=', start_date), ('scheduled_date', '<=', end_date)]
        elif filter == 'delivery_orders_done':
            domain = [('picking_type_code', '=', 'outgoing'),('is_expired_tranfer', '=', False), ('state', '=', 'done'), ('scheduled_date', '>=', start_date), ('scheduled_date', '<=', end_date)]
        elif filter == 'intrawarehouse_transfer_done':
            domain = [('is_interwarehouse_transfer', '=', True), ('state', '=', 'done'), ('scheduled_date', '>=', start_date), ('scheduled_date', '<=', end_date)]
        for picking_id in self.env['stock.picking'].search(domain, order=sort):
            vals = {}
            vals['picking_id'] = picking_id.id
            vals['name'] = picking_id.name
            vals['backorder'] = picking_id.backorder_id.name if picking_id.backorder_id else ''
            vals['ref'] = picking_id.origin or ''
            vals['floor'] = ''
            vals['date_scheduled'] = str(picking_id.scheduled_date) if picking_id.scheduled_date else ''
            vals['partner'] = picking_id.partner_id.name_get()[0][1] if picking_id.partner_id else ''
            vals['status'] = status_dict.get(picking_id.state, '')
            vals['color'] = color_dict.get(picking_id.state, '')
            vals['src_location'] = picking_id.location_id.name_get()[0][1]
            vals['dest_location'] = picking_id.location_dest_id.name_get()[0][1]
            vals['location'] = vals['src_location'] + ' → ' + vals['dest_location']
            vals['warehouse_id'] = picking_id.warehouse_id.name if picking_id.warehouse_id else ''
            data_list.append(vals)
        return data_list

    def get_locations(self, picking_type_code):
        location_id = False
        location_dest_id = False
        stock_locations_ids = self.env['stock.location'].search([])
        user = self.env.user
        if user.branch_ids:
            branch_ids = user.branch_ids.ids
        else:
            branch_ids = self.env['res.branch'].search([]).ids
            branch_ids.extend([False])
        if picking_type_code == "outgoing":
            filter_dest_location_ids = stock_locations_ids.filtered(lambda r:r.usage != 'internal' and r.branch_id.id in branch_ids).ids
            filter_source_location_ids = stock_locations_ids.filtered(lambda r:r.usage == 'internal' and r.branch_id.id in branch_ids).ids
        elif picking_type_code == "incoming":
            filter_dest_location_ids = stock_locations_ids.filtered(lambda r:r.usage == 'internal' and r.branch_id.id in branch_ids).ids
            filter_source_location_ids = stock_locations_ids.filtered(lambda r:r.usage != 'internal' and r.branch_id.id in branch_ids).ids
        else:
            filter_dest_location_ids = stock_locations_ids.ids
            filter_source_location_ids = stock_locations_ids.ids
        if picking_type_code == 'outgoing':
            location_dest_id = self.env.ref('stock.stock_location_customers').id
        if picking_type_code == 'incoming':
            location_id = self.env.ref('stock.stock_location_suppliers').id
        location_id = location_id and self.env['stock.location'].browse(location_id).read(['complete_name'])[0] or False
        location_dest_id = location_dest_id and self.env['stock.location'].browse(location_dest_id).read(['complete_name'])[0] or False
        source_location_ids = filter_source_location_ids and self.env['stock.location'].browse(filter_source_location_ids).read(['complete_name']) or False
        dest_location_ids = filter_dest_location_ids and self.env['stock.location'].browse(filter_dest_location_ids).read(['complete_name']) or False

        return {
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'source_location_ids': source_location_ids,
            'dest_location_ids': dest_location_ids,
        }

    def get_picking_transfer_data(self):
        self.ensure_one()
        data_list = []
        for move_id in self.move_lines:
            vals = {}
            product_id = move_id.product_id
            vals['move_id'] = move_id.id
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode
            vals['item_no'] = product_id.default_code
            vals['qty'] = move_id.product_uom_qty
            vals['tracking'] = product_id.tracking
            vals['scanned_qty'] = move_id.reserved_availability
            quants_dict = {}
            scanned_qty = 0.0
            quant_list = []
            if product_id.tracking != 'none':
                for move_line in move_id.move_line_ids.filtered(lambda l: l.lot_id):
                    lot_id = move_line.lot_id
                    if lot_id.id in quants_dict:
                        quants_dict[lot_id.id]['scanned_qty'] += move_line.product_uom_qty
                    else:
                        quant_vals = {}
                        quant_vals['lot_name'] = lot_id.name
                        quant_vals['lot_id'] = lot_id.id
                        quant_vals['scanned_qty'] = move_line.product_uom_qty
                        quants_dict[lot_id.id] = quant_vals
            for key in quants_dict.keys():
                scanned_qty += quants_dict[key]['scanned_qty']
                quant_list.append(quants_dict[key])
            vals['scanned_data'] = quant_list
            available_qty = move_id.reserved_availability
            for quant in self.env['stock.quant'].search(
                    [('location_id', '=', move_id.location_id.id), ('product_id', '=', move_id.product_id.id)]):
                available_qty += quant.available_quantity
            vals['available_qty'] = available_qty
            vals['unreserved_quants'] = self.get_unreserved_quants(move_id)
            data_list.append(vals)
        return data_list

    def get_unreserved_quants(self, move_id):
        if not self:
            return []
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
                if quant.available_quantity > 0:
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

    # Create Stock Picking
    def create_stock_picking(self, code, data_dict):
        if not data_dict.get('line_list', []):
            return ''
        location_id = self.env['stock.picking'].get_location_id(data_dict.get('src_location', ''))
        location_dest_id = self.env['stock.picking'].get_location_id(data_dict.get('dest_location', ''))
        if code == 'incoming':
            picking_type_id = self.env['stock.picking.type'].search(
                [('default_location_dest_id', '=', location_dest_id), ('code', '=', code)], limit=1)
        else:
            picking_type_id = self.env['stock.picking.type'].search(
                [('default_location_src_id', '=', location_id), ('code', '=', code)], limit=1)
        if not picking_type_id:
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', code)], limit=1)
        vals = {}
        vals['picking_type_id'] = picking_type_id.id
        vals['location_id'] = location_id
        vals['location_dest_id'] = location_dest_id
        vals['origin'] = data_dict.get('ref', '')
        vals['scheduled_date'] = data_dict['date'] if data_dict.get('date', False) else str(datetime.now())[:19]
        vals['partner_id'] = data_dict.get('partner_id', False)
        picking_id = self.env['stock.picking'].create(vals)
        for line_dict in data_dict.get('line_list', []):
            move_vals = {}
            product_id = self.env['product.product'].browse(line_dict.get('product_id', False))
            move_vals['picking_id'] = picking_id.id
            move_vals['product_id'] = line_dict.get('product_id', False)
            move_vals['name'] = product_id.name
            move_vals['date'] = data_dict['date'] if data_dict.get('date', False) else str(datetime.now())[:19]
            move_vals['product_uom_qty'] = float(line_dict.get('qty', 0))
            move_vals['product_uom'] = product_id.uom_id.id if product_id.uom_id else False
            move_vals['location_id'] = location_id
            move_vals['location_dest_id'] = location_dest_id
            self.env['stock.move'].create(move_vals)

        vals2 = {}
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        if picking_id:
            vals2['picking_id'] = picking_id.id
            vals2['name'] = picking_id.name
            vals2['date_scheduled'] = str(picking_id.scheduled_date) if picking_id.scheduled_date else ''
            vals2['partner'] = picking_id.partner_id.name_get()[0][1] if picking_id.partner_id else ''
            vals2['status'] = status_dict.get(picking_id.state, '')
            vals2['src_location'] = picking_id.location_id.name_get()[0][1]
            vals2['dest_location'] = picking_id.location_dest_id.name_get()[0][1]
            vals2['backorder'] = picking_id.backorder_id.name if picking_id.backorder_id else ''
            vals2['color'] = color_dict.get(picking_id.state, '')
        return vals2

    # Get Location id by name
    def get_location_id(self, location_name):
        for location_id in self.env['stock.location'].search([]):
            if location_id.name_get()[0][1] == location_name:
                return location_id.id
        return False

    # Incoming get data for APP
    def get_incoming_data(self):
        self.ensure_one()
        data_list = []
        for move_id in self.move_lines:
            vals = {}
            product_id = move_id.product_id
            vals['move_id'] = move_id.id
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['qty'] = move_id.product_qty
            vals['tracking'] = product_id.tracking
            vals['scanned_qty'] = move_id.quantity_done
            vals['package_type'] = move_id.package_type.name if move_id.package_type and move_id.package_type.name else ''
            vals['package_type_id'] = move_id.package_type.id if move_id.package_type else 0
            vals['qty_in_pack'] = move_id.qty_in_pack
            vals['qty_per_lot'] = move_id.qty_per_lot
            scanned_data = []
            # if product_id.tracking != 'none':
            for move_line in move_id.move_line_nosuggest_ids:
                scanned_data.append({'lot_name': move_line.lot_name or '', 'qty': move_line.qty_done, 'result_package_id': move_line.result_package_id.name if move_line.result_package_id else '', 'location_dest_id': move_line.location_dest_id.display_name or ''})
            vals['scanned_data'] = scanned_data
            data_list.append(vals)
        return data_list

    def app_action_assign(self, data_list):
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        self.ensure_one()
        if self.state not in ['confirmed', 'partially_available', 'assigned']:
            return {'error_message': False, 'state': status_dict[self.state], 'color': color_dict[self.state]}
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
                        self.env['stock.move.line'].create(vals)
                    move_id.write({'quantity_done': data.get('qty', 0), 'picking_type_id': self.picking_type_id.id})
        else:
            data_list = filter(lambda x: x.get('qty') > 0, data_list)
            self.with_context(picking_reserve=data_list).action_assign()
        return {'error_message': True, 'state': status_dict[self.state], 'color': color_dict[self.state]}

    def app_action_validate(self, data_list):
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        self.ensure_one()
        if self.picking_type_code != 'incoming':
            self.app_action_assign(data_list)
        if self.state not in ['confirmed', 'partially_available', 'assigned']:
            return {'error_message': False, 'state': status_dict[self.state], 'color': color_dict[self.state]}
        transfer_dict = self.button_validate()
        if type(transfer_dict) == dict and transfer_dict.get('res_model'):
            if transfer_dict['res_model'] == 'stock.immediate.transfer':
                wiz_obj = self.env[transfer_dict['res_model']].with_context(transfer_dict['context']).create({})
                wiz_obj.process()
                if self.state == 'assigned':
                    backorder_dict = self.button_validate()
                    if type(backorder_dict) == dict and backorder_dict.get('res_model', '') == 'stock.backorder.confirmation':
                        wiz_obj = self.env[backorder_dict['res_model']].with_context(backorder_dict['context']).create({})
                        wiz_obj.process()
                    elif type(backorder_dict) == dict and backorder_dict.get('res_model', '') == 'expiry.picking.confirmation':
                        wiz_obj = self.env[backorder_dict['res_model']].with_context(backorder_dict['context']).create({})
                        wiz_obj.process()
            elif transfer_dict['res_model'] == 'stock.backorder.confirmation':
                wiz_obj = self.env[transfer_dict['res_model']].with_context(transfer_dict['context']).create({})
                wiz_obj.process()
        backorder = self.search([('backorder_id', '=', self.id)], order='id desc', limit=1)
        if backorder:
            backorder.do_unreserve()
        return {'error_message': True, 'state': status_dict[self.state], 'color': color_dict[self.state]}


StockPicking()
