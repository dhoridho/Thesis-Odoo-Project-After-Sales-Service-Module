# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from odoo import tools

class InternalTransfer(models.Model):
    _inherit = "internal.transfer"

    def get_app_button(self):
        button_list = []
        if self.state3 == 'draft': #draft
            button_list.append({'button_name': 'REQUEST FOR APPROVAL', 'button_method': 'button_request_for_approval'})
        elif self.state3 == 'to_approve': #Waiting For Approval
            button_list.append({'button_name': 'REST TO DRAFT', 'button_method': 'button_reset_to_draft'})
            button_list.append({'button_name': 'APPROVE', 'button_method': 'button_approve'})
        elif self.state3 == 'approved': #Approved
            button_list.append({'button_name': 'CONFIRM', 'button_method': 'button_confirm'})
        elif self.state3 == 'confirm': #Confirmed
            button_list.append({'button_name': 'DONE', 'button_method': 'button_done'})
            button_list.append({'button_name': 'CANCEL', 'button_method': 'button_cancel'})
        return button_list

    def button_request_for_approval(self):
        error_message = 'success'
        try:
            self.itr_request_for_approving()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state3, ''), 'error_message': error_message, 'color': color_dict.get(self.state3, '')}

    def button_approve(self):
        error_message = 'success'
        try:
            self.itr_approving()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state3, ''), 'error_message': error_message, 'color': color_dict.get(self.state3, '')}

    def button_reset_to_draft(self):
        error_message = 'success'
        try:
            self.itr_reset_to_draft()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state3, ''), 'error_message': error_message, 'color': color_dict.get(self.state3, '')}

    def button_confirm(self):
        error_message = 'success'
        try:
            self.action_confirm()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state3, ''), 'error_message': error_message, 'color': color_dict.get(self.state3, '')}

    def button_done(self):
        error_message = 'success'
        try:
            self.action_done()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state3, ''), 'error_message': error_message, 'color': color_dict.get(self.state3, '')}

    def button_cancel(self):
        error_message = 'success'
        try:
            self.action_cancel()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state3, ''), 'error_message': error_message, 'color': color_dict.get(self.state3, '')}

    def get_interwarehouse_transfer_request_list(self, sort='id asc', filter=False, start_date=False, end_date=False):
        data_list = []
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}
        if filter == 'done':
            domain = [('state3', '=', 'done'), ('scheduled_date', '>=', start_date), ('scheduled_date', '<=', end_date)]
        else:
           domain = [('state3', 'in', ['draft', 'to_approve', 'approved', 'confirm'])]
        for transfer_id in self.env['internal.transfer'].search(domain, order=sort):
            vals = {}
            vals['name'] = transfer_id.name
            vals['transfer_id'] = transfer_id.id
            vals['requested_by'] = transfer_id.requested_by.name if transfer_id.requested_by else ''
            vals['status'] = status_dict.get(transfer_id.state3, '')
            vals['color'] = color_dict.get(transfer_id.state3, '')
            vals['src_warehouse'] = transfer_id.source_warehouse_id.name_get()[0][1] if transfer_id.source_warehouse_id else ''
            vals['src_location'] = transfer_id.source_location_id.name_get()[0][1] if transfer_id.source_location_id else ''
            vals['dest_warehouse'] = transfer_id.destination_warehouse_id.name_get()[0][1] if transfer_id.destination_warehouse_id else ''
            vals['dest_location'] = transfer_id.destination_location_id.name_get()[0][1] if transfer_id.destination_location_id else ''
            vals['location'] = vals['src_location'] + ' → ' + vals['dest_location']
            vals['scheduled_date'] = str(transfer_id.scheduled_date) if transfer_id.scheduled_date else ''
            data_list.append(vals)
        return data_list

    def get_interwarehouse_transfer_request_data(self):
        self.ensure_one()
        data_list = []
        for line_id in self.product_line_ids:
            vals = {}
            product_id = line_id.product_id
            vals['line_id'] = line_id.id
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['qty'] = line_id.qty
            vals['tracking'] = product_id.tracking
            data_list.append(vals)
        return data_list

    # Create internal transfer
    def create_internal_transfer(self, data_dict):
        if not data_dict.get('line_list', []):
            return ''
        src_warehouse_id = self.env['internal.transfer'].get_warehouse_id(data_dict.get('src_warehouse', ''))
        dest_warehouse_id = self.env['internal.transfer'].get_warehouse_id(data_dict.get('dest_warehouse', ''))
        location_source_id = self.env['internal.transfer'].get_location_id(data_dict.get('src_location', ''))
        location_dest_id = self.env['internal.transfer'].get_location_id(data_dict.get('dest_location', ''))

        vals = {}
        vals['source_warehouse_id'] = src_warehouse_id
        vals['destination_warehouse_id'] = dest_warehouse_id
        vals['source_location_id'] = location_source_id
        vals['destination_location_id'] = location_dest_id
        vals['scheduled_date'] = data_dict['date'] if data_dict.get('date', False) else str(datetime.now())[:19]
        line_data =[]
        for line_dict in data_dict.get('line_list', []):
            line_vals = {}
            product_id = self.env['product.product'].browse(line_dict.get('product_id', False))
            line_vals['product_id'] = line_dict.get('product_id', False)
            line_vals['description'] = product_id.name
            line_vals['qty'] = float(line_dict.get('qty', 0))
            line_vals['scheduled_date'] = data_dict['date'] if data_dict.get('date', False) else str(datetime.now())[:19]
            line_vals['uom'] = product_id.uom_id.id if product_id.uom_id else False
            line_vals['destination_location_id'] = location_dest_id
            line_vals['source_location_id'] = location_source_id
            line_data.append((0, 0, line_vals))
        vals['product_line_ids'] = line_data
        transfer_id = self.env['internal.transfer'].create(vals)
        transfer_id.onchange_source_loction_id()
        transfer_id.onchange_dest_loction_id()

        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}

        vals2 = {}
        if transfer_id:
            vals2['name'] = transfer_id.name
            vals2['transfer_id'] = transfer_id.id
            vals2['requested_by'] = transfer_id.requested_by.name if transfer_id.requested_by else ''
            vals2['status'] = status_dict.get(transfer_id.state3, '')
            vals2['color'] = color_dict.get(transfer_id.state3, '')
            vals2['src_warehouse'] = transfer_id.source_warehouse_id.name_get()[0][1] if transfer_id.source_warehouse_id else ''
            vals2['src_location'] = transfer_id.source_location_id.name_get()[0][1] if transfer_id.source_location_id else ''
            vals2['dest_warehouse'] = transfer_id.destination_warehouse_id.name_get()[0][1] if transfer_id.destination_warehouse_id else ''
            vals2['dest_location'] = transfer_id.destination_location_id.name_get()[0][1] if transfer_id.destination_location_id else ''
            vals2['scheduled_date'] = str(transfer_id.scheduled_date) if transfer_id.scheduled_date else ''
        return vals2

    # Get Location id by name
    def get_location_id(self, location_name):
        for location_id in self.env['stock.location'].search([]):
            if location_id.name_get()[0][1] == location_name:
                return location_id.id
        return False

    #Get Warehouse by name
    def get_warehouse_id(self, warehouse_name):
        for warehouse_id in self.env['stock.warehouse'].search([]):
            if warehouse_id.name_get()[0][1] == warehouse_name:
                return warehouse_id.id
        return False

InternalTransfer()