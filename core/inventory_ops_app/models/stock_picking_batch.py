# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from datetime import datetime, date
from odoo import tools


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    def app_custom_button(self):
        button_list = []
        if self.state == 'draft':
            button_list.append({'button_name': 'Confirm', 'button_method': 'button_action_confirm'})
        elif self.state == 'in_progress':
            button_list.append({'button_name': 'Check Availability', 'button_method': 'button_action_assign'})
            button_list.append({'button_name': 'validate', 'button_method': 'button_action_validate'})
            button_list.append({'button_name': 'Force validate', 'button_method': 'button_action_force_validate'})
        return button_list

    def button_action_confirm(self):
        error_message = 'success'
        try:
            self.action_confirm()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'in_progress': 'In progress', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'in_progress': '#efb139','done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    def button_action_assign(self):
        error_message = 'success'
        try:
            self.action_assign()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'in_progress': 'In progress', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'in_progress': '#efb139', 'done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    def button_action_force_validate(self):
        error_message = 'success'
        try:
           result = self.action_force_validate()
           if type(result) == bool and result is True:
               error_message = 'success'
           elif type(result) == dict and result.get('res_model', '') == 'stock.backorder.confirmation':
               error_message = "Cannot validate due to backorder product, please check server..."
           elif type(result) == dict and result.get('res_model', '') == 'expiry.picking.confirmation':
               error_message = "Cannot validate due to expired product, please check server..."
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'in_progress': 'In progress', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'in_progress': '#efb139', 'done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    def button_action_validate(self):
        error_message = 'success'
        try:
            result = self.action_done()
            if type(result) == bool and result is True:
                error_message = 'success'
            elif type(result) == dict and result.get('res_model', '') == 'stock.backorder.confirmation':
                error_message = "Cannot validate due to backorder product, please check server..."
            elif type(result) == dict and result.get('res_model', '') == 'expiry.picking.confirmation':
                error_message = "Cannot validate due to expired product, please check server..."
            elif type(result) == dict and result.get('res_model', '') == 'stock.immediate.transfer':
                self.action_force_validate()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'in_progress': 'In progress', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'in_progress': '#efb139', 'done': '#262628'}
        return {'state': status_dict[self.state], 'error_message': error_message, 'color': color_dict[self.state]}

    def get_batch_picking_list(self, sort='id desc', filter=False, start_date=False, end_date=False):
        data_list = []
        color_dict = {'draft': '#82C7D2', 'in_progress': '#efb139', 'done': '#262628'}
        if filter == 'done':
            domain = [('state', '=', 'done'), ('create_date', '>=', start_date), ('create_date', '<=', end_date)]
        else:
            domain = [('state', 'not in', ['cancel','done'])]
        for batch_id in self.env['stock.picking.batch'].search(domain, order=sort):
            vals = {}
            vals['batch_picking_id'] = batch_id.id
            vals['name'] = batch_id.name
            vals['state'] = dict(batch_id.fields_get(['state'])['state']['selection'])[batch_id.state]
            vals['date'] = str(batch_id.scheduled_date) if batch_id.scheduled_date else ''
            vals['color'] = color_dict.get(batch_id.state, '')
            vals['warehouse_id'] = batch_id.warehouse_id.id if batch_id.warehouse_id else 0
            vals['warehouse'] = batch_id.warehouse_id.name if batch_id.warehouse_id else ''
            vals['company_id'] = batch_id.company_id.id if batch_id.company_id else 0
            vals['company'] = batch_id.company_id.name if batch_id.company_id else ''
            location_list = [record.name_get()[0][1] for record in list(set(batch_id.location_ids))]
            vals['locations'] = ", ".join(location_list)
            data_list.append(vals)
        return data_list

    def get_batch_transfer_data(self):
        data_list = []
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting Another Operation', 'confirmed': 'Waiting',
                       'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        for line in self.picking_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['reference'] = line.name
            vals['scheduled_date'] = str(line.scheduled_date) if line.scheduled_date else ''
            vals['source_document'] = line.origin if line.origin else ''
            vals['state'] = status_dict.get(line.state, '')
            vals['color'] = color_dict.get(line.state, '')
            data_list.append(vals)
        return data_list

    def get_batch_picking_data(self):
        data_list = []
        for line in self.stock_picking_batch_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['product_id'] = line.product_id.id
            vals['product'] = line.product_id.name
            vals['demand_qty'] = line.demand_qty
            vals['reserved_qty'] = line.reserved_qty
            vals['done_qty'] = line.done_qty
            vals['uom'] = line.uom_id.name if line.uom_id else ''
            vals['uom_id'] = line.uom_id.id if line.uom_id else 0
            data_list.append(vals)
        return data_list

    def create_batch_picking_app(self, data_dict):
        vals = {}
        location_list = []
        vals['user_id'] = data_dict.get('user_id', False)
        vals['warehouse_id'] = data_dict.get('warehouse_id', False)
        location_list += [(int(record)) for record in data_dict['location_ids']]
        vals['location_ids'] = [(6,0,location_list)]
        vals['branch_id'] = data_dict.get('branch_id', False)
        vals['company_id'] = data_dict.get('company_id', False)
        vals['scheduled_date'] = data_dict['scheduled_date'] if data_dict.get('scheduled_date', False) else str(datetime.now())[:19]
        batch_id = self.env['stock.picking.batch'].create(vals)

        color_dict = {'draft': '#82C7D2', 'in_progress': '#efb139', 'done': '#262628'}
        vals2 = {}
        if batch_id:
            vals2['batch_picking_id'] = batch_id.id
            vals2['name'] = batch_id.name
            vals2['state'] = dict(batch_id.fields_get(['state'])['state']['selection'])[batch_id.state]
            vals2['date'] = str(batch_id.scheduled_date) if batch_id.scheduled_date else ''
            vals2['color'] = color_dict.get(batch_id.state, '')
            vals2['warehouse_id'] = batch_id.warehouse_id.id if batch_id.warehouse_id else 0
            vals2['warehouse'] = batch_id.warehouse_id.name if batch_id.warehouse_id else ''
            vals2['company_id'] = batch_id.company_id.id if batch_id.company_id else 0
            vals2['company'] = batch_id.company_id.name if batch_id.company_id else ''
            location_list = [record.name_get()[0][1] for record in list(set(batch_id.location_ids))]
            vals2['locations'] = ", ".join(location_list)
        return vals2

    def app_get_locations(self, warehouse_id):
        location_ids = []
        location_obj = self.env['stock.location']
        warehouse_obj = self.env['stock.warehouse'].browse(warehouse_id)
        store_location_id = warehouse_obj.view_location_id.id
        addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
        for location in addtional_ids:
            if location.location_id.id not in addtional_ids.ids:
                location_ids.append(location.id)
        child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
        final_location = child_location_ids + location_ids
        location_object = self.env['stock.location'].search_read([('id', 'in', final_location)], ['id','display_name'])
        branch_id = warehouse_obj.branch_id.id if warehouse_obj.branch_id else 0
        branch = warehouse_obj.branch_id.name if warehouse_obj.branch_id else ''
        return {'locations': location_object, 'branch_id': branch_id, 'branch': branch}

    def app_transfer_data(self, list_ids):
        allowed_picking_states = ['waiting', 'confirmed', 'assigned']

        for batch in self:
            domain_states = list(allowed_picking_states)
            domain = [
                ('company_id', '=', batch.company_id.id),
                ('is_consignment', '=', False),
                ('state', 'in', domain_states),
            ]
            if batch.location_ids:
                domain += [('location_id', 'in', batch.location_ids.ids), ('picking_type_code', 'in', ('outgoing', 'internal')), ('id','not in', list_ids)]
            data_obj = self.env['stock.picking'].search(domain, order="id desc")

        data_list = []

        status_dict = {'draft': 'Draft', 'waiting': 'Waiting Another Operation', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#60000000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        for record in data_obj:
            vals = {}
            vals['id'] = record.id
            vals['name'] = record.name
            vals['scheduled_date'] = str(record.scheduled_date) if record.scheduled_date else ''
            vals['origin'] = record.origin  if record.origin else ''
            vals['state'] = status_dict.get(record.state, '')
            vals['color'] = color_dict.get(record.state, '')
            vals['batch_id'] = record.batch_id.id if record.batch_id else 0
            vals['batch'] = record.batch_id.name if record.batch_id else ''
            data_list.append(vals)
        return data_list