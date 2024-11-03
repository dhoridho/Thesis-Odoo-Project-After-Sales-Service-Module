# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
from odoo import tools

class InternalTransfer(models.Model):
    _inherit = "internal.transfer"

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT 
                  ru.id AS user_id,
                  COALESCE(ru.interwarehouse_request_unlink_data, '') AS interwarehouse_request_unlink_data
                FROM
                  res_users as ru
                WHERE 
                  ru.active != FALSE	AND ru.share = FALSE
                ORDER BY 
                  user_id asc
            '''
            self.env.cr.execute(query)
            users_data = self.env.cr.dictfetchall()
            for record in users_data:
                user_id = record.get('user_id')
                old_value = record.get('interwarehouse_request_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET interwarehouse_request_unlink_data =%s WHERE id =%s""", (new_value, user_id))
                self._cr.commit()
        return res

    def get_interwarehouse_request_data(self):
        query = '''
            SELECT
                it.id AS transfer_id,
                it.name,
                it.state,
                COALESCE(rp.name, '') AS requested_by,
                CASE
                  WHEN it.state = 'draft' THEN 'Draft'
                  WHEN it.state = 'to_approve' THEN 'Waiting For Approval'
                  WHEN it.state = 'approved' THEN 'Approved'
                  WHEN it.state = 'confirm' THEN 'Confirmed'
                  WHEN it.state = 'done' THEN 'Done'
                  ELSE it.state
                END AS status,
                CASE
                  WHEN it.state = 'draft' THEN '#E7DFDE'
                  WHEN it.state = 'to_approve' THEN '#efb139'
                  WHEN it.state = 'approved' THEN '#efb139'
                  WHEN it.state = 'confirm' THEN '#008000'
                  WHEN it.state = 'done' THEN '#262628'
                  ELSE '#FFA500'
                END AS color,
                COALESCE(sw.name, '') AS src_warehouse,
                COALESCE(sw1.name, '') AS dest_warehouse,
                COALESCE(sl.complete_name, '') AS src_location,
                COALESCE(sl1.complete_name, '') AS dest_location,
                CONCAT(sl.complete_name, ' → ', sl1.complete_name) AS location,
                it.scheduled_date,
                date(it.scheduled_date) AS date_filtered
                FROM 
                internal_transfer it
                LEFT JOIN res_users ru ON (it.requested_by = ru.id)
                LEFT JOIN res_partner rp ON (ru.partner_id = rp.id)
                LEFT JOIN stock_warehouse sw ON (it.source_warehouse_id = sw.id)
                LEFT JOIN stock_warehouse sw1 ON (it.destination_warehouse_id = sw1.id)
                LEFT JOIN stock_location sl ON (it.source_location_id = sl.id)
                LEFT JOIN stock_location sl1 ON (it.destination_location_id = sl1.id)
                WHERE it.state NOT IN ('cancel', 'rejected')
                ORDER BY transfer_id asc;
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.interwarehouse_request_date = datetime.now()
        return result

    def get_interwarehouse_request_line_data(self):
        query = '''
        SELECT
            itl.id AS line_id,
            itl.product_line AS transfer_id,
            itl.product_id,
            CONCAT('[', pp.default_code, '] ', pt.name) AS product,
            COALESCE(pp.barcode, '') AS barcode, 
            COALESCE(pp.default_code, '') AS item_no,
            pt.tracking,
            COALESCE(itl.qty, 0.0) AS qty,
            COALESCE(uu.id, 0) AS uom_id,
			COALESCE(uu.name,'') AS uom
            FROM
            internal_transfer_line itl
            LEFT JOIN internal_transfer it ON (itl.product_line = it.id)
            LEFT JOIN product_product pp ON (itl.product_id = pp.id) 
            LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
            LEFT JOIN uom_uom uu ON (itl.uom = uu.id)
            WHERE 
            itl.product_line is not null AND
            it.state NOT IN ('cancel', 'rejected')
            ORDER BY 
            line_id desc;
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.interwarehouse_request_line_date = datetime.now()
        return result

    def get_dynamic_interwarehouse_request_data(self):
        it_datetime = self.env.user.interwarehouse_request_date or datetime.now()
        query = '''
            SELECT
                it.id AS transfer_id,
                it.name,
                it.state,
                COALESCE(rp.name, '') AS requested_by,
                CASE
                  WHEN it.state = 'draft' THEN 'Draft'
                  WHEN it.state = 'to_approve' THEN 'Waiting For Approval'
                  WHEN it.state = 'approved' THEN 'Approved'
                  WHEN it.state = 'confirm' THEN 'Confirmed'
                  WHEN it.state = 'done' THEN 'Done'
                  ELSE it.state
                END AS status,
                CASE
                  WHEN it.state = 'draft' THEN '#E7DFDE'
                  WHEN it.state = 'to_approve' THEN '#efb139'
                  WHEN it.state = 'approved' THEN '#efb139'
                  WHEN it.state = 'confirm' THEN '#008000'
                  WHEN it.state = 'done' THEN '#262628'
                  ELSE '#FFA500'
                END AS color,
                COALESCE(sw.name, '') AS src_warehouse,
                COALESCE(sw1.name, '') AS dest_warehouse,
                COALESCE(sl.complete_name, '') AS src_location,
                COALESCE(sl1.complete_name, '') AS dest_location,
                CONCAT(sl.complete_name, ' → ', sl1.complete_name) AS location,
                it.scheduled_date,
                date(it.scheduled_date) AS date_filtered
                FROM 
                internal_transfer it
                LEFT JOIN res_users ru ON (it.requested_by = ru.id)
                LEFT JOIN res_partner rp ON (ru.partner_id = rp.id)
                LEFT JOIN stock_warehouse sw ON (it.source_warehouse_id = sw.id)
                LEFT JOIN stock_warehouse sw1 ON (it.destination_warehouse_id = sw1.id)
                LEFT JOIN stock_location sl ON (it.source_location_id = sl.id)
                LEFT JOIN stock_location sl1 ON (it.destination_location_id = sl1.id)
                WHERE it.write_date >= '%s' OR it.create_date >= '%s'
                ORDER BY transfer_id asc;
        '''%(it_datetime,it_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.interwarehouse_request_date = datetime.now()
        return result

    def get_dynamic_interwarehouse_request_line_data(self):
        itl_datetime = self.env.user.interwarehouse_request_line_date or datetime.now()
        query = '''
        SELECT
            itl.id AS line_id,
            itl.product_line AS transfer_id,
            itl.product_id,
            CONCAT('[', pp.default_code, '] ', pt.name) AS product,
            COALESCE(pp.barcode, '') AS barcode, 
            COALESCE(pp.default_code, '') AS item_no,
            pt.tracking,
            COALESCE(itl.qty, 0.0) AS qty,
            COALESCE(uu.id, 0) AS uom_id,
			COALESCE(uu.name,'') AS uom
            FROM
            internal_transfer_line itl
            LEFT JOIN internal_transfer it ON (itl.product_line = it.id)
            LEFT JOIN product_product pp ON (itl.product_id = pp.id) 
            LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
            LEFT JOIN uom_uom uu ON (itl.uom = uu.id)
            WHERE 
            itl.product_line is not null AND itl.write_date >= '%s' OR itl.create_date >= '%s'
            ORDER BY 
            line_id desc;
        '''%(itl_datetime,itl_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.interwarehouse_request_line_date = datetime.now()
        return result

    def app_interwarehouse_transfer_request_button_data(self):
        vals2 = {}
        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved','confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000','done': '#262628'}
        vals2['name'] = self.name
        vals2['transfer_id'] = self.id
        vals2['requested_by'] = self.requested_by.name if self.requested_by else ''
        vals2['state'] = self.state3
        vals2['status'] = status_dict.get(self.state3, '')
        vals2['color'] = color_dict.get(self.state3, '')
        vals2['src_warehouse'] = self.source_warehouse_id.name_get()[0][1] if self.source_warehouse_id else ''
        vals2['src_location'] = self.source_location_id.name_get()[0][1] if self.source_location_id else ''
        vals2['dest_warehouse'] = self.destination_warehouse_id.name_get()[0][1] if self.destination_warehouse_id else ''
        vals2['dest_location'] = self.destination_location_id.name_get()[0][1] if self.destination_location_id else ''
        vals2['scheduled_date'] = str(self.scheduled_date) if self.scheduled_date else ''
        vals2['date_filtered'] = str(self.scheduled_date).split(" ")[0] if self.scheduled_date else ""
        vals2['location'] = vals2['src_location'] + ' → ' + vals2['dest_location']
        data_list = []
        for line_id in self.product_line_ids:
            vals = {}
            product_id = line_id.product_id
            vals['line_id'] = line_id.id
            vals['transfer_id'] = line_id.product_line.id
            vals['product_id'] = product_id.id
            vals['product'] = '[' + product_id.default_code + '] ' + product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['qty'] = line_id.qty
            vals['tracking'] = product_id.tracking
            vals['uom_id'] = line_id.uom.id if line_id.uom else 0
            vals['uom'] = line_id.uom.name if line_id.uom else ''
            data_list.append(vals)
        vals2['interwarehouse_line_data'] = data_list
        return vals2

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

    def get_all_interwarehouse_buttons(self):
        button_list = []
        # draft
        button_list.append({'button_name': 'REQUEST FOR APPROVAL', 'button_method': 'button_request_for_approval', 'button_state': 'draft'})
        # to_approve
        button_list.append({'button_name': 'REST TO DRAFT', 'button_method': 'button_reset_to_draft', 'button_state': 'to_approve'})
        button_list.append({'button_name': 'APPROVE', 'button_method': 'button_approve', 'button_state': 'to_approve'})
        # approved
        button_list.append({'button_name': 'CONFIRM', 'button_method': 'button_confirm', 'button_state': 'approved'})
        # confirm
        button_list.append({'button_name': 'DONE', 'button_method': 'button_done', 'button_state': 'confirm'})
        button_list.append({'button_name': 'CANCEL', 'button_method': 'button_cancel', 'button_state': 'confirm'})
        return button_list

    def button_request_for_approval(self):
        error_message = 'success'
        try:
            self.itr_request_for_approving()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        interwarehouse_data = self.app_interwarehouse_transfer_request_button_data()
        return {'interwarehouse_data': interwarehouse_data ,'error_message': error_message}

    def button_approve(self):
        error_message = 'success'
        try:
            self.itr_approving()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        interwarehouse_data = self.app_interwarehouse_transfer_request_button_data()
        return {'interwarehouse_data': interwarehouse_data, 'error_message': error_message}

    def button_reset_to_draft(self):
        error_message = 'success'
        try:
            self.itr_reset_to_draft()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        interwarehouse_data = self.app_interwarehouse_transfer_request_button_data()
        return {'interwarehouse_data': interwarehouse_data, 'error_message': error_message}

    def button_confirm(self):
        error_message = 'success'
        try:
            self.action_confirm()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        interwarehouse_data = self.app_interwarehouse_transfer_request_button_data()
        return {'interwarehouse_data': interwarehouse_data, 'error_message': error_message}

    def button_done(self):
        error_message = 'success'
        try:
            self.action_done()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        interwarehouse_data = self.app_interwarehouse_transfer_request_button_data()
        return {'interwarehouse_data': interwarehouse_data, 'error_message': error_message}

    def button_cancel(self):
        error_message = 'success'
        try:
            self.action_cancel()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        interwarehouse_data = self.app_interwarehouse_transfer_request_button_data()
        return {'interwarehouse_data': interwarehouse_data, 'error_message': error_message}

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
            vals['uom_id'] = line_id.uom.id if line_id.uom else 0
            vals['uom'] = line_id.uom.name if line_id.uom else ''
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
            line_vals['uom'] = line_dict.get('uom_id', 0) #product_id.uom_id.id if product_id.uom_id else False
            line_vals['destination_location_id'] = location_dest_id
            line_vals['source_location_id'] = location_source_id
            line_data.append((0, 0, line_vals))
        vals['product_line_ids'] = line_data
        transfer_id = self.env['internal.transfer'].create(vals)
        transfer_id._onchange_warehouse_id_for_location()
        transfer_id.onchange_source_loction_id()
        transfer_id.onchange_dest_loction_id()
        transfer_id.branch_id = transfer_id.source_warehouse_id.branch_id.id

        status_dict = {'draft': 'Draft', 'to_approve': 'Waiting For Approval', 'approved': 'Approved', 'confirm': 'Confirmed', 'done': 'Done'}
        color_dict = {'draft': '#E7DFDE', 'to_approve': '#efb139', 'approved': '#efb139', 'confirm': '#008000', 'done': '#262628'}

        vals2 = {}
        if transfer_id:
            vals2['name'] = transfer_id.name
            vals2['transfer_id'] = transfer_id.id
            vals2['requested_by'] = transfer_id.requested_by.name if transfer_id.requested_by else ''
            vals2['state'] = transfer_id.state3
            vals2['status'] = status_dict.get(transfer_id.state3, '')
            vals2['color'] = color_dict.get(transfer_id.state3, '')
            vals2['src_warehouse'] = transfer_id.source_warehouse_id.name_get()[0][1] if transfer_id.source_warehouse_id else ''
            vals2['src_location'] = transfer_id.source_location_id.name_get()[0][1] if transfer_id.source_location_id else ''
            vals2['dest_warehouse'] = transfer_id.destination_warehouse_id.name_get()[0][1] if transfer_id.destination_warehouse_id else ''
            vals2['dest_location'] = transfer_id.destination_location_id.name_get()[0][1] if transfer_id.destination_location_id else ''
            vals2['scheduled_date'] = str(transfer_id.scheduled_date) if transfer_id.scheduled_date else ''
            vals2['date_filtered'] = str(transfer_id.scheduled_date).split(" ")[0] if transfer_id.scheduled_date else ""
            vals2['location'] = vals2['src_location'] + ' → ' + vals2['dest_location']
            data_list = []
            for line_id in transfer_id.product_line_ids:
                vals = {}
                product_id = line_id.product_id
                vals['line_id'] = line_id.id
                vals['transfer_id'] = line_id.product_line.id
                vals['product_id'] = product_id.id
                vals['product'] = '[' + product_id.default_code + '] ' + product_id.name
                vals['barcode'] = product_id.barcode or ''
                vals['item_no'] = product_id.default_code or ''
                vals['qty'] = line_id.qty
                vals['tracking'] = product_id.tracking
                vals['uom_id'] = line_id.uom.id if line_id.uom else 0
                vals['uom'] = line_id.uom.name if line_id.uom else ''
                data_list.append(vals)
            vals2['interwarehouse_line_data'] = data_list
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


class InternalTransferLine(models.Model):
    _inherit = 'internal.transfer.line'

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT 
                  ru.id AS user_id,
                  COALESCE(ru.interwarehouse_line_request_unlink_data, '') AS interwarehouse_line_request_unlink_data
                FROM
                  res_users as ru
                WHERE 
                  ru.active != FALSE	AND ru.share = FALSE
                ORDER BY 
                  user_id asc
            '''
            self.env.cr.execute(query)
            users_data = self.env.cr.dictfetchall()
            for record in users_data:
                user_id = record.get('user_id')
                old_value = record.get('interwarehouse_line_request_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET interwarehouse_line_request_unlink_data =%s WHERE id =%s""",(new_value, user_id))
                self._cr.commit()
        return res