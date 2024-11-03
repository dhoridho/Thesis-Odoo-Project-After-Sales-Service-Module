# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import datetime
from odoo import tools


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT
                  ru.id AS user_id,
                  COALESCE(ru.picking_unlink_data, '') AS picking_unlink_data
                FROM
                  res_users as ru
                WHERE
                  ru.active != FALSE AND ru.share = FALSE
                ORDER BY
                  user_id asc
            '''
            self.env.cr.execute(query)
            users_data = self.env.cr.dictfetchall()
            for record in users_data:
                user_id = record.get('user_id')
                old_value = record.get('picking_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET picking_unlink_data =%s WHERE id =%s""", (new_value, user_id))
                self._cr.commit()
        return res

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

    def app_picking_buttons(self):
        button_list = []
        # incoming
        button_list.append({'button_name': 'MARK AS TODO', 'button_method': 'app_action_confirm', 'button_state': 'draft', 'picking_type_code': 'incoming'})
        button_list.append({'button_name': 'VALIDATE', 'button_method': 'app_button_validate', 'button_state': 'assigned', 'picking_type_code': 'incoming'})
        # button_list.append({'button_name': 'CHECK AVAILABILITY', 'button_method': 'button_check_availability', 'button_state': 'confirmed', 'picking_type_code': 'incoming'})
        # button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate', 'button_state': 'confirmed', 'picking_type_code': 'incoming'})
        # outgoing
        button_list.append({'button_name': 'MARK AS TODO', 'button_method': 'app_action_confirm', 'button_state': 'draft', 'picking_type_code': 'outgoing'})
        button_list.append({'button_name': 'VALIDATE', 'button_method': 'app_button_validate', 'button_state': 'assigned', 'picking_type_code': 'outgoing'})
        # button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve', 'button_state': 'assigned', 'picking_type_code': 'outgoing'})
        # button_list.append({'button_name': 'CHECK AVAILABILITY', 'button_method': 'button_check_availability', 'button_state': 'confirmed', 'picking_type_code': 'outgoing'})
        # button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate', 'button_state': 'confirmed', 'picking_type_code': 'outgoing'})
        # button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve', 'button_state': 'confirmed', 'picking_type_code': 'outgoing'})
        # internal
        button_list.append({'button_name': 'MARK AS TODO', 'button_method': 'app_action_confirm', 'button_state': 'draft', 'picking_type_code': 'internal'})
        button_list.append({'button_name': 'VALIDATE', 'button_method': 'app_button_validate', 'button_state': 'assigned', 'picking_type_code': 'internal'})
        # button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve', 'button_state': 'assigned', 'picking_type_code': 'internal'})
        # button_list.append({'button_name': 'CHECK AVAILABILITY', 'button_method': 'button_check_availability', 'button_state': 'confirmed', 'picking_type_code': 'internal'})
        # button_list.append({'button_name': 'VALIDATE', 'button_method': 'button_action_validate', 'button_state': 'confirmed', 'picking_type_code': 'internal'})
        # button_list.append({'button_name': 'UNRESERVE', 'button_method': 'button_unreserve', 'button_state': 'confirmed', 'picking_type_code': 'internal'})
        return button_list

    def button_mark_as_todo(self):
        error_message = 'success'
        try:
            self.action_confirm()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        picking_data = self.app_stock_picking_retrive_data()
        return {'stock_picking_data': picking_data, 'error_message': error_message}

    def button_check_availability(self):
        error_message = 'success'
        try:
            self.action_assign()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        picking_data = self.app_stock_picking_retrive_data()
        return {'stock_picking_data': picking_data, 'error_message': error_message}

    def button_unreserve(self):
        error_message = 'success'
        try:
            self.do_unreserve()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        picking_data = self.app_stock_picking_retrive_data()
        return {'stock_picking_data': picking_data, 'error_message': error_message}

    def app_stock_picking_retrive_data(self):
        vals2 = {}
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#600000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        vals2['picking_id'] = self.id
        vals2['name'] = self.name
        vals2['scheduled_date'] = str(self.scheduled_date) if self.scheduled_date else ''
        vals2['partner'] = self.partner_id.name_get()[0][1] if self.partner_id else ''
        vals2['status'] = status_dict.get(self.state, '')
        vals2['src_location'] = self.location_id.name_get()[0][1]
        vals2['dest_location'] = self.location_dest_id.name_get()[0][1]
        vals2['backorder'] = self.backorder_id.name if self.backorder_id else ''
        vals2['color'] = color_dict.get(self.state, '')
        vals2['origin'] = self.origin or ''
        vals2['partner_id'] = self.partner_id.id if self.partner_id else 0
        vals2['backorder_id'] = self.backorder_id.id if self.backorder_id else 0
        vals2['state'] = self.state or ''
        vals2['location_id'] = self.location_id.id if self.location_id else 0
        vals2['location_dest_id'] = self.location_dest_id.id if self.location_dest_id else 0
        vals2['location'] = vals2['src_location'] + ' → ' + vals2['dest_location']
        vals2['sp_warehouse_id'] = self.warehouse_id.id if self.warehouse_id else 0
        vals2['sp_warehouse'] = self.warehouse_id.name if self.warehouse_id else ''
        vals2['spt_warehouse_id'] = self.picking_type_id.warehouse_id.id if self.picking_type_id.warehouse_id else 0
        vals2['spt_warehouse'] = self.picking_type_id.warehouse_id.name if self.picking_type_id.warehouse_id else ''
        vals2['picking_type_id'] = self.picking_type_id.id if self.picking_type_id else ''
        vals2['picking_type_code'] = self.picking_type_id.code if self.picking_type_id else ''
        vals2['is_expired_tranfer'] = False  # self.is_expired_tranfer if self.is_expired_tranfer else False
        vals2['is_interwarehouse_transfer'] = self.is_interwarehouse_transfer if self.is_interwarehouse_transfer else False
        vals2['date_filtered'] = str(self.scheduled_date).split(" ")[0] if self.scheduled_date else ""

        data_list = []
        for move_id in self.move_lines:
            vals = {}
            product_id = move_id.product_id
            vals['move_id'] = move_id.id
            vals['picking_id'] = move_id.picking_id.id
            vals['product_id'] = product_id.id
            default_code = product_id.default_code or ''
            vals['product'] = '[' + default_code + '] ' + product_id.name
            vals['barcode'] = move_id.temp_barcode or ''
            vals['item_no'] = product_id.default_code or ''
            vals['tracking'] = product_id.tracking
            vals['qty'] = move_id.product_uom_qty
            if move_id.picking_id.picking_type_code == 'incoming':
                vals['scanned_qty'] = move_id.quantity_done
                vals['previous_qty'] = move_id.quantity_done
            elif move_id.picking_id.picking_type_code == 'outgoing':
                vals['scanned_qty'] = move_id.reserved_availability
                vals['previous_qty'] = move_id.reserved_availability
            elif move_id.picking_id.picking_type_code == 'internal':
                vals['scanned_qty'] = move_id.reserved_availability
                vals['previous_qty'] = move_id.reserved_availability
            else:
                vals['scanned_qty'] = move_id.quantity_done
                vals['previous_qty'] = move_id.quantity_done
            vals['done_qty'] = move_id.quantity_done
            vals[
                'package_type'] = move_id.package_type.name if move_id.package_type and move_id.package_type.name else ''
            vals['package_type_id'] = move_id.package_type.id if move_id.package_type else 0
            vals['qty_in_pack'] = move_id.qty_in_pack
            vals['qty_per_lot'] = move_id.qty_per_lot
            vals['product_uom_id'] = move_id.product_uom.id if move_id.product_uom else 0
            vals['product_uom'] = move_id.product_uom.name if move_id.product_uom else ''
            available_qty = move_id.reserved_availability
            for quant in self.env['stock.quant'].search(
                    [('location_id', '=', move_id.location_id.id), ('product_id', '=', move_id.product_id.id)]):
                available_qty += quant.available_quantity
            vals['available_quantity'] = available_qty
            data_list.append(vals)
        vals2['picking_line_data'] = data_list
        scanned_data = []
        for move_id in self.move_lines:
            total_qty = sum(move_id.move_line_nosuggest_ids.mapped('qty_done'))
            for move_line in move_id.move_line_nosuggest_ids:
                scanned_data.append({
                    'picking_id': move_line.picking_id.id if move_line.picking_id else 0,
                    'move_id': move_line.move_id.id if move_line.move_id else 0,
                    'batch_serial_no': move_line.lot_id.name if move_line.lot_id else move_line.lot_name or '',
                    'scan_qty': move_line.qty_done,
                    'prevscan_qty': move_line.qty_done,
                    'result_package_id': move_line.result_package_id.name if move_line.result_package_id else '',
                    'location_dest_id': move_line.location_dest_id.display_name or '',
                    'overall_qty': move_id.product_qty,
                    'overallscanned_qty': total_qty
                })
        vals2['stock_move_line_data'] = scanned_data
        return vals2

        # List View - Receiving, Picking and Internal Transfer
    def get_picking_list(self, wh_id, picking_type_code, filter, sort='id asc', start_date=False, end_date=False):
        data_list = []
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
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
            domain = [('picking_type_code', '=', 'incoming'), ('is_expired_tranfer', '=', False),
                      ('state', "not in", ('done', 'cancel', 'rejected'))]
        elif filter == 'delivery_orders':
            domain = [('picking_type_code', '=', 'outgoing'), ('is_expired_tranfer', '=', False),
                      ('state', "not in", ('done', 'cancel'))]
        elif filter == 'intrawarehouse_transfer':
            domain = [('is_interwarehouse_transfer', '=', True), ('state', "not in", ('done', 'cancel'))]
        elif filter == 'receiving_notes_done':
            domain = [('picking_type_code', '=', 'incoming'), ('is_expired_tranfer', '=', False),
                      ('state', '=', 'done'), ('scheduled_date', '>=', start_date),
                      ('scheduled_date', '<=', end_date)]
        elif filter == 'delivery_orders_done':
            domain = [('picking_type_code', '=', 'outgoing'), ('is_expired_tranfer', '=', False),
                      ('state', '=', 'done'), ('scheduled_date', '>=', start_date),
                      ('scheduled_date', '<=', end_date)]
        elif filter == 'intrawarehouse_transfer_done':
            domain = [('is_interwarehouse_transfer', '=', True), ('state', '=', 'done'),
                      ('scheduled_date', '>=', start_date), ('scheduled_date', '<=', end_date)]
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

    def get_picking_data(self):
        query = '''
            SELECT
                sp.id AS picking_id,
                sp.name,
                COALESCE(sp.origin, '') AS origin,
                sp.scheduled_date,
                date(sp.scheduled_date) AS date_filtered,
                COALESCE(sp.partner_id, 0) AS partner_id,
                COALESCE(rp.name, '') AS partner,
                COALESCE(sp.backorder_id, 0) AS backorder_id,
                COALESCE(spb.name, '') AS backorder,
                sp.state,
                CASE
                    WHEN sp.state = 'draft' THEN 'Draft'
                    WHEN sp.state = 'waiting' THEN 'Waiting Another Operation'
                    WHEN sp.state = 'confirmed' THEN 'Waiting'
                    WHEN sp.state = 'assigned' THEN 'Ready'
                    WHEN sp.state = 'approved' THEN 'Approved'
                    WHEN sp.state = 'waiting_for_approval' THEN 'Waiting for Approval'
                    WHEN sp.state = 'done' THEN 'Done'
                    ELSE sp.state
                END AS status,
                CASE
                    WHEN sp.state = 'draft' THEN '#600000'
                    WHEN sp.state = 'waiting' THEN '#EFB139'
                    WHEN sp.state = 'confirmed' THEN '#EFB139'
                    WHEN sp.state = 'assigned' THEN '#008000'
                    WHEN sp.state = 'approved' THEN '#33A961'
                    WHEN sp.state = 'waiting_for_approval' THEN '#EFB139'
                    WHEN sp.state = 'done' THEN '#262628'
                    ELSE '#FFA500'
                END AS color,
                sp.location_id,
                sls.complete_name AS src_location,
                sp.location_dest_id,
                sld.complete_name AS dest_location,
                CONCAT(sls.complete_name, ' → ', sld.complete_name) AS location,
                COALESCE(sp.warehouse_id, 0) AS sp_warehouse_id,
                COALESCE(sw_sp.name, '') AS sp_warehouse,
                COALESCE(spt.warehouse_id, 0) AS spt_warehouse_id,
                COALESCE(sw_spt.name, '') AS spt_warehouse,
                sp.picking_type_id,
                spt.code AS picking_type_code,
                COALESCE(sp.is__expired_tranfer, false) AS is_expired_tranfer,
                COALESCE(sp.is_interwarehouse_transfer, false) AS is_interwarehouse_transfer
                FROM
                stock_picking sp
                LEFT JOIN res_partner rp ON (sp.partner_id = rp.id)
                LEFT JOIN stock_location sls ON (sp.location_id = sls.id)
                LEFT JOIN stock_warehouse sw_sp ON (sp.warehouse_id = sw_sp.id)
                LEFT JOIN stock_picking spb ON (sp.backorder_id = spb.id)
                LEFT JOIN stock_location sld ON (sp.location_dest_id = sld.id)
                LEFT JOIN stock_picking_type spt ON (sp.picking_type_id = spt.id)
                LEFT JOIN stock_warehouse sw_spt ON (spt.warehouse_id = sw_spt.id)
                WHERE sp.state NOT IN ('cancel', 'rejected')
                ORDER BY picking_id asc;
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.picking_date = datetime.now()
        return result

    # Need to add unreserved_quants from get_unreserved_quants method
    def get_picking_line_data(self, picking_id):
        # query = '''
        #     SELECT
        #       sm.id AS move_id,
        #       sm.picking_id,
        #       sm.product_id,
        #       CONCAT(
        #         '[', pp.default_code, '] ', pt.name
        #       ) AS product,
        #       COALESCE(sm.temp_barcode, '') AS barcode,
        #       COALESCE(pp.default_code, '') AS item_no,
        #       pt.tracking,
        #       COALESCE(sm.product_uom_qty, 0.0) AS qty,
        #       --COALESCE(sm.quantity_done, 0.0) AS scanned_qty,
        #       --COALESCE(sm.quantity_done, 0.0) AS previous_qty,
        #       COALESCE(sm.package_type, 0) AS package_type_id,
        #       COALESCE(ppg.name, '') AS package_type,
        #       sm.picking_type_code,
        #       CASE
		# 	      WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
		# 		  WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
		# 		  WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
		# 	      ELSE 0.0
		# 	  END AS scanned_qty,
		# 	  CASE
		# 	      WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
		# 		  WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
		# 		  WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
		# 		  ELSE 0.0
		# 	  END AS previous_qty,
		# 	  COALESCE(sm.quantity_done, 0.0) AS done_qty,
        #       sm.qty_in_pack,
        #       COALESCE(sm.qty_per_lot, 0.0) AS qty_per_lot,
        #       COALESCE(
        #         (
        #           select
        #             sum(
        #               sq.quantity - sq.reserved_quantity
        #             ) AS available_quantity
        #           from
        #             stock_quant as sq
        #           WHERE
        #             sq.location_id = sm.location_id
        #             AND sq.product_id = sm.product_id
        #         ), 0.0) AS available_quantity,
        #       COALESCE(uu.id, 0) AS product_uom_id,
		# 	  COALESCE(uu.name, '') AS product_uom
        #     FROM
        #       stock_move sm
        #       LEFT JOIN product_product pp ON (sm.product_id = pp.id)
        #       LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
        #       LEFT JOIN product_packaging ppg ON (sm.package_type = ppg.id)
        #       LEFT JOIN stock_picking sp ON (sm.picking_id = sp.id)
        #       --LEFT JOIN stock_move_line sml ON (sm.id = sml.move_id)
        #       LEFT JOIN uom_uom uu ON (sm.product_uom = uu.id)
        #     WHERE
        #       sm.picking_id is not null AND
        #       sp.state NOT IN ('cancel', 'rejected')
        #     ORDER BY
        #       move_id asc;
        # '''
        query = f'''
            WITH available_quantities AS (
            SELECT
                sq.product_id,
                sq.location_id,
                SUM(sq.quantity - sq.reserved_quantity) AS available_quantity
            FROM
                stock_quant sq
            GROUP BY
                sq.product_id, sq.location_id
        )
        SELECT
            sm.id AS move_id,
            sm.picking_id,
            sm.product_id,
            CONCAT('[', pp.default_code, '] ', pt.name) AS product,
            COALESCE(sm.temp_barcode, '') AS barcode,
            COALESCE(pp.default_code, '') AS item_no,
            pt.tracking,
            COALESCE(sm.product_uom_qty, 0.0) AS qty,
            COALESCE(sm.package_type, 0) AS package_type_id,
            COALESCE(ppg.name, '') AS package_type,
            sm.picking_type_code,
            CASE
                WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
                WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                ELSE 0.0
            END AS scanned_qty,
            CASE
                WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
                WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                ELSE 0.0
            END AS previous_qty,
            COALESCE(sm.quantity_done, 0.0) AS done_qty,
            sm.qty_in_pack,
            COALESCE(sm.qty_per_lot, 0.0) AS qty_per_lot,
            COALESCE(aq.available_quantity, 0.0) AS available_quantity,
            COALESCE(uu.id, 0) AS product_uom_id,
            COALESCE(uu.name, '') AS product_uom,
            sm.exp_date,
            COALESCE(sml.lot_name, '') AS lot_name
        FROM
            stock_move_line sml
            LEFT JOIN stock_move sm ON sml.move_id = sm.id
            LEFT JOIN product_product pp ON sm.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN product_packaging ppg ON sm.package_type = ppg.id
            LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
            LEFT JOIN uom_uom uu ON sm.product_uom = uu.id
            LEFT JOIN available_quantities aq ON sm.product_id = aq.product_id AND sm.location_id = aq.location_id
        WHERE
            sm.picking_id = {picking_id}
        ORDER BY
            move_id ASC;
        '''

        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.picking_line_date = datetime.now()
        return result
    
    def get_picking_line_by_id(self, picking_id):
        query = f'''
                WITH available_quantities AS (
                SELECT
                    sq.product_id,
                    sq.location_id,
                    SUM(sq.quantity - sq.reserved_quantity) AS available_quantity
                FROM
                    stock_quant sq
                GROUP BY
                    sq.product_id, sq.location_id
            )
            SELECT
                sm.id AS move_id,
                sm.picking_id,
                sm.product_id,
                CONCAT('[', pp.default_code, '] ', pt.name) AS product,
                COALESCE(sm.temp_barcode, '') AS barcode,
                COALESCE(pp.default_code, '') AS item_no,
                pt.tracking,
                COALESCE(sm.product_uom_qty, 0.0) AS qty,
                COALESCE(sm.package_type, 0) AS package_type_id,
                COALESCE(ppg.name, '') AS package_type,
                sm.picking_type_code,
                CASE
                    WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
                    WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                    WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                    ELSE 0.0
                END AS scanned_qty,
                CASE
                    WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
                    WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                    WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
                    ELSE 0.0
                END AS previous_qty,
                COALESCE(sm.quantity_done, 0.0) AS done_qty,
                sm.qty_in_pack,
                COALESCE(sm.qty_per_lot, 0.0) AS qty_per_lot,
                COALESCE(aq.available_quantity, 0.0) AS available_quantity,
                COALESCE(uu.id, 0) AS product_uom_id,
                COALESCE(uu.name, '') AS product_uom,
                sm.exp_date,
                COALESCE(sml.lot_name, '') AS lot_name
            FROM
                stock_move_line sml
                LEFT JOIN stock_move sm ON sml.move_id = sm.id
                LEFT JOIN product_product pp ON sm.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN product_packaging ppg ON sm.package_type = ppg.id
                LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                LEFT JOIN uom_uom uu ON sm.product_uom = uu.id
                LEFT JOIN available_quantities aq ON sm.product_id = aq.product_id AND sm.location_id = aq.location_id
            WHERE
                sm.picking_id = {picking_id}
            ORDER BY
                move_id ASC;
            '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.picking_line_date = datetime.now()
        return result

    def get_move_line_data(self):
        query = '''
            SELECT
            COALESCE(sml.picking_id, 0) AS picking_id,
            COALESCE(sml.move_id, 0) AS move_id,
            COALESCE(sml.qty_done, 0.0) AS scan_qty,
            COALESCE(sml.qty_done, 0.0) AS prevscan_qty,
            --COALESCE(spl.name, '') AS batch_serial_no,
            COALESCE(spl.name, sml.lot_name, '') AS batch_serial_no,
            COALESCE(sqp.name, '') AS result_package_id,
            COALESCE(sl.complete_name, '') AS location_dest_id,
			COALESCE(sm2.product_qty, 0.0) AS overall_qty,
			--COALESCE(sml.product_id, 0) AS product_id,
			--COALESCE(sml.product_qty, 0.0) AS product_qty,
		    COALESCE((
			  SELECT
				SUM(sml2.qty_done)
			  FROM
				stock_move_line AS sml2
				LEFT JOIN stock_move sm3 ON (sml2.move_id = sm3.id)
			  WHERE
				sml2.move_id = sml.move_id
			  GROUP BY
				sml2.move_id
			 ), 0.00) AS overallscanned_qty
            FROM
            stock_move_line as sml
            LEFT JOIN stock_location sl ON (sml.location_dest_id = sl.id)
            LEFT JOIN stock_quant_package sqp ON (sml.result_package_id = sqp.id)
			LEFT JOIN stock_move sm2 ON (sml.move_id = sm2.id)
			LEFT JOIN stock_production_lot spl ON (sml.lot_id = spl.id)
            '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.move_line_date = datetime.now()
        return result

    # Dynamic api call
    def get_dynamic_picking_data(self):
        sp_datetime = self.env.user.picking_date or datetime.now()
        query = '''
            SELECT
                sp.id AS picking_id,
                sp.name,
                COALESCE(sp.origin, '') AS origin,
                sp.scheduled_date,
                date(sp.scheduled_date) AS date_filtered,
                COALESCE(sp.partner_id, 0) AS partner_id,
                COALESCE(rp.name, '') AS partner,
                COALESCE(sp.backorder_id, 0) AS backorder_id,
                COALESCE(spb.name, '') AS backorder,
                sp.state,
                CASE
                    WHEN sp.state = 'draft' THEN 'Draft'
                    WHEN sp.state = 'waiting' THEN 'Waiting Another Operation'
                    WHEN sp.state = 'confirmed' THEN 'Waiting'
                    WHEN sp.state = 'assigned' THEN 'Ready'
                    WHEN sp.state = 'approved' THEN 'Approved'
                    WHEN sp.state = 'waiting_for_approval' THEN 'Waiting for Approval'
                    WHEN sp.state = 'done' THEN 'Done'
                    ELSE sp.state
                END AS status,
                CASE
                    WHEN sp.state = 'draft' THEN '#600000'
                    WHEN sp.state = 'waiting' THEN '#EFB139'
                    WHEN sp.state = 'confirmed' THEN '#EFB139'
                    WHEN sp.state = 'assigned' THEN '#008000'
                    WHEN sp.state = 'approved' THEN '#33A961'
                    WHEN sp.state = 'waiting_for_approval' THEN '#EFB139'
                    WHEN sp.state = 'done' THEN '#262628'
                    ELSE '#FFA500'
                END AS color,
                sp.location_id,
                sls.complete_name AS src_location,
                sp.location_dest_id,
                sld.complete_name AS dest_location,
                CONCAT(sls.complete_name, ' → ', sld.complete_name) AS location,
                COALESCE(sp.warehouse_id, 0) AS sp_warehouse_id,
                COALESCE(sw_sp.name, '') AS sp_warehouse,
                COALESCE(spt.warehouse_id, 0) AS spt_warehouse_id,
                COALESCE(sw_spt.name, '') AS spt_warehouse,
                sp.picking_type_id,
                spt.code AS picking_type_code,
                COALESCE(sp.is__expired_tranfer, false) AS is_expired_tranfer,
                COALESCE(sp.is_interwarehouse_transfer, false) AS is_interwarehouse_transfer
                FROM
                stock_picking sp
                LEFT JOIN res_partner rp ON (sp.partner_id = rp.id)
                LEFT JOIN stock_location sls ON (sp.location_id = sls.id)
                LEFT JOIN stock_warehouse sw_sp ON (sp.warehouse_id = sw_sp.id)
                LEFT JOIN stock_picking spb ON (sp.backorder_id = spb.id)
                LEFT JOIN stock_location sld ON (sp.location_dest_id = sld.id)
                LEFT JOIN stock_picking_type spt ON (sp.picking_type_id = spt.id)
                LEFT JOIN stock_warehouse sw_spt ON (spt.warehouse_id = sw_spt.id)
                WHERE sp.write_date >= '%s' OR sp.create_date >= '%s'
                ORDER BY picking_id asc;
        '''%(sp_datetime,sp_datetime)

        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.picking_date = datetime.now()
        return result

    def get_dynamic_picking_line_data(self):
        spl_datetime = self.env.user.picking_line_date or datetime.now()
        query = '''
            SELECT
              sm.id AS move_id,
              sm.picking_id,
              sm.product_id,
              CONCAT(
                '[', pp.default_code, '] ', pt.name
              ) AS product,
              COALESCE(sm.temp_barcode, '') AS barcode,
              COALESCE(pp.default_code, '') AS item_no,
              pt.tracking,
              COALESCE(sm.product_uom_qty, 0.0) AS qty,
              --COALESCE(sm.quantity_done, 0.0) AS scanned_qty,
              --COALESCE(sm.quantity_done, 0.0) AS previous_qty,
              COALESCE(sm.package_type, 0) AS package_type_id,
              COALESCE(ppg.name, '') AS package_type,
              sm.picking_type_code,
              CASE
			      WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
				  WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
				  WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
			      ELSE 0.0
			  END AS scanned_qty,
			  CASE
			      WHEN sm.picking_type_code = 'incoming' THEN COALESCE(sm.quantity_done, 0.0)
				  WHEN sm.picking_type_code = 'outgoing' THEN COALESCE(sm.reserved_availability_stored, 0.0)
				  WHEN sm.picking_type_code = 'internal' THEN COALESCE(sm.reserved_availability_stored, 0.0)
				  ELSE 0.0
			  END AS previous_qty,
			  COALESCE(sm.quantity_done, 0.0) AS done_qty,
              sm.qty_in_pack,
              COALESCE(sm.qty_per_lot, 0.0) AS qty_per_lot,
              COALESCE(
                (
                  select
                    sum(
                      sq.quantity - sq.reserved_quantity
                    ) AS available_quantity
                  from
                    stock_quant as sq
                  WHERE
                    sq.location_id = sm.location_id
                    AND sq.product_id = sm.product_id
                ), 0.0) AS available_quantity,
              COALESCE(uu.id, 0) AS product_uom_id,
			  COALESCE(uu.name, '') AS product_uom
            FROM
              stock_move sm
              LEFT JOIN product_product pp ON (sm.product_id = pp.id)
              LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
              LEFT JOIN product_packaging ppg ON (sm.package_type = ppg.id)
              LEFT JOIN stock_picking sp ON (sm.picking_id = sp.id)
              --LEFT JOIN stock_move_line sml ON (sm.id = sml.move_id)
              LEFT JOIN uom_uom uu ON (sm.product_uom = uu.id)
            WHERE
              sm.picking_id is not null AND sm.write_date >= '%s' OR sm.create_date >= '%s'
            ORDER BY
              move_id asc;
        '''%(spl_datetime, spl_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.picking_line_date = datetime.now()
        return result

    def get_dynamic_move_line_data(self):
        sml_datetime = self.env.user.move_line_date or datetime.now()
        query = '''
            SELECT
            COALESCE(sml.picking_id, 0) AS picking_id,
            COALESCE(sml.move_id, 0) AS move_id,
            COALESCE(sml.qty_done, 0.0) AS scan_qty,
            COALESCE(sml.qty_done, 0.0) AS prevscan_qty,
            --COALESCE(spl.name, '') AS batch_serial_no,
            COALESCE(spl.name, sml.lot_name, '') AS batch_serial_no,
            COALESCE(sqp.name, '') AS result_package_id,
            COALESCE(sl.complete_name, '') AS location_dest_id,
            COALESCE(sm2.product_qty, 0.0) AS overall_qty,
            --COALESCE(sml.product_id, 0) AS product_id,
            --COALESCE(sml.product_qty, 0.0) AS product_qty,
            COALESCE((
              SELECT
                SUM(sml2.qty_done)
              FROM
                stock_move_line AS sml2
                LEFT JOIN stock_move sm3 ON (sml2.move_id = sm3.id)
              WHERE
                sml2.move_id = sml.move_id
              GROUP BY
                sml2.move_id
             ), 0.00) AS overallscanned_qty
            FROM
                stock_move_line as sml
                LEFT JOIN stock_location sl ON (sml.location_dest_id = sl.id)
                LEFT JOIN stock_quant_package sqp ON (sml.result_package_id = sqp.id)
                LEFT JOIN stock_move sm2 ON (sml.move_id = sm2.id)
                LEFT JOIN stock_production_lot spl ON (sml.lot_id = spl.id)
            WHERE sml.write_date >= '%s' OR sml.create_date >= '%s'
            '''%(sml_datetime, sml_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.move_line_date = datetime.now()
        return result

    # def get_locations(self, picking_type_code):
    #     location_id = False
    #     location_dest_id = False
    #     stock_locations_ids = self.env['stock.location'].search([])
    #     user = self.env.user
    #     if user.branch_ids:
    #         branch_ids = user.branch_ids.ids
    #     else:
    #         branch_ids = self.env['res.branch'].search([]).ids
    #         branch_ids.extend([False])
    #     if picking_type_code == "outgoing":
    #         filter_dest_location_ids = stock_locations_ids.filtered(lambda r:r.usage != 'internal' and r.branch_id.id in branch_ids).ids
    #         filter_source_location_ids = stock_locations_ids.filtered(lambda r:r.usage == 'internal' and r.branch_id.id in branch_ids).ids
    #     elif picking_type_code == "incoming":
    #         filter_dest_location_ids = stock_locations_ids.filtered(lambda r:r.usage == 'internal' and r.branch_id.id in branch_ids).ids
    #         filter_source_location_ids = stock_locations_ids.filtered(lambda r:r.usage != 'internal' and r.branch_id.id in branch_ids).ids
    #     else:
    #         filter_dest_location_ids = stock_locations_ids.ids
    #         filter_source_location_ids = stock_locations_ids.ids
    #     if picking_type_code == 'outgoing':
    #         location_dest_id = self.env.ref('stock.stock_location_customers').id
    #     if picking_type_code == 'incoming':
    #         location_id = self.env.ref('stock.stock_location_suppliers').id
    #     location_id = location_id and self.env['stock.location'].browse(location_id).read(['complete_name'])[0] or False
    #     location_dest_id = location_dest_id and self.env['stock.location'].browse(location_dest_id).read(['complete_name'])[0] or False
    #     source_location_ids = filter_source_location_ids and self.env['stock.location'].browse(filter_source_location_ids).read(['complete_name']) or False
    #     dest_location_ids = filter_dest_location_ids and self.env['stock.location'].browse(filter_dest_location_ids).read(['complete_name']) or False
    #
    #     return {
    #         'location_id': location_id,
    #         'location_dest_id': location_dest_id,
    #         'source_location_ids': source_location_ids,
    #         'dest_location_ids': dest_location_ids,
    #     }

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
            vals['product_uom_id'] = move_id.product_uom.id if move_id.product_uom else 0
            vals['product_uom'] = move_id.product_uom.name if move_id.product_uom else ''
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
        vals['branch_id'] = data_dict.get('branch_id', False)
        if data_dict.get('is_adhoc_transfer', False):
            vals['branch_id'] = self.env.user.branch_id.id or False
        picking_id = self.env['stock.picking'].create(vals)
        for line_dict in data_dict.get('line_list', []):
            move_vals = {}
            product_id = self.env['product.product'].browse(line_dict.get('product_id', False))
            move_vals['picking_id'] = picking_id.id
            move_vals['product_id'] = line_dict.get('product_id', False)
            move_vals['name'] = product_id.name
            move_vals['date'] = data_dict['date'] if data_dict.get('date', False) else str(datetime.now())[:19]
            move_vals['product_uom_qty'] = float(line_dict.get('qty', 0))
            move_vals['product_uom'] = line_dict.get("uom_id", 0)  #product_id.uom_id.id if product_id.uom_id else False
            move_vals['location_id'] = location_id
            move_vals['location_dest_id'] = location_dest_id
            move_vals['picking_type_id'] = picking_type_id.id
            self.env['stock.move'].create(move_vals)

        vals2 = {}
        status_dict = {'draft': 'Draft', 'waiting': 'Waiting', 'confirmed': 'Waiting', 'assigned': 'Ready',
                       'approved': 'Approved', 'waiting_for_approval': 'Waiting for Approval', 'done': 'Done'}
        color_dict = {'draft': '#600000', 'waiting': '#efb139', 'confirmed': '#efb139', 'assigned': '#008000',
                      'approved': '#33A961', 'waiting_for_approval': '#efb139', 'done': '#262628'}
        if picking_id:
            vals2['picking_id'] = picking_id.id
            vals2['name'] = picking_id.name
            vals2['scheduled_date'] = str(picking_id.scheduled_date) if picking_id.scheduled_date else ''
            vals2['partner'] = picking_id.partner_id.name_get()[0][1] if picking_id.partner_id else ''
            vals2['status'] = status_dict.get(picking_id.state, '')
            vals2['src_location'] = picking_id.location_id.name_get()[0][1]
            vals2['dest_location'] = picking_id.location_dest_id.name_get()[0][1]
            vals2['backorder'] = picking_id.backorder_id.name if picking_id.backorder_id else ''
            vals2['color'] = color_dict.get(picking_id.state, '')
            vals2['origin'] = picking_id.origin or ''
            vals2['partner_id'] = picking_id.partner_id.id if picking_id.partner_id else 0
            vals2['backorder_id'] = picking_id.backorder_id.id if picking_id.backorder_id else 0
            vals2['state'] = picking_id.state or ''
            vals2['location_id'] = picking_id.location_id.id if picking_id.location_id else 0
            vals2['location_dest_id'] = picking_id.location_dest_id.id if picking_id.location_dest_id else 0
            vals2['location'] = vals2['src_location'] + ' → ' + vals2['dest_location']
            vals2['sp_warehouse_id'] = picking_id.warehouse_id.id if picking_id.warehouse_id else 0
            vals2['sp_warehouse'] = picking_id.warehouse_id.name if picking_id.warehouse_id else ''
            vals2['spt_warehouse_id'] = picking_id.picking_type_id.warehouse_id.id if picking_id.picking_type_id.warehouse_id else 0
            vals2['spt_warehouse'] = picking_id.picking_type_id.warehouse_id.name if picking_id.picking_type_id.warehouse_id else ''
            vals2['picking_type_id'] = picking_id.picking_type_id.id if picking_id.picking_type_id else ''
            vals2['picking_type_code'] = picking_id.picking_type_id.code if picking_id.picking_type_id else ''
            vals2['is_expired_tranfer'] = False  #picking_id.is_expired_tranfer if picking_id.is_expired_tranfer else False
            vals2['is_interwarehouse_transfer'] = picking_id.is_interwarehouse_transfer if picking_id.is_interwarehouse_transfer else False
            vals2['date_filtered'] = str(picking_id.scheduled_date).split(" ")[0] if picking_id.scheduled_date else ""

            data_list = []
            for move_id in picking_id.move_lines:
                vals = {}
                product_id = move_id.product_id
                vals['move_id'] = move_id.id
                vals['picking_id'] = move_id.picking_id.id
                vals['product_id'] = product_id.id
                default_code = product_id.default_code or ''
                vals['product'] = '[' + default_code + '] ' + product_id.name
                vals['barcode'] = move_id.temp_barcode or ''
                vals['item_no'] = product_id.default_code or ''
                vals['tracking'] = product_id.tracking
                vals['qty'] = move_id.product_uom_qty
                vals['scanned_qty'] = move_id.quantity_done
                vals['previous_qty'] = move_id.quantity_done
                vals['done_qty'] = move_id.quantity_done
                vals['package_type'] = move_id.package_type.name if move_id.package_type and move_id.package_type.name else ''
                vals['package_type_id'] = move_id.package_type.id if move_id.package_type else 0
                vals['qty_in_pack'] = move_id.qty_in_pack
                vals['qty_per_lot'] = move_id.qty_per_lot
                vals['product_uom_id'] = move_id.product_uom.id if move_id.product_uom else 0
                vals['product_uom'] = move_id.product_uom.name if move_id.product_uom else ''
                available_qty = move_id.reserved_availability
                for quant in self.env['stock.quant'].search(
                        [('location_id', '=', move_id.location_id.id), ('product_id', '=', move_id.product_id.id)]):
                    available_qty += quant.available_quantity
                vals['available_quantity'] = available_qty
                data_list.append(vals)
            vals2['picking_line_data'] = data_list
            scanned_data = []
            for move_id in picking_id.move_lines:
                total_qty = sum(move_id.move_line_nosuggest_ids.mapped('qty_done'))
                for move_line in move_id.move_line_nosuggest_ids:
                    scanned_data.append({
                        'picking_id': move_line.picking_id.id if move_line.picking_id else 0,
                        'move_id': move_line.move_id.id if move_line.move_id else 0,
                        'batch_serial_no': move_line.lot_id.name if move_line.lot_id else move_line.lot_name or '',
                        'scan_qty': move_line.qty_done,
                        'prevscan_qty': move_line.qty_done,
                        'result_package_id': move_line.result_package_id.name if move_line.result_package_id else '',
                        'location_dest_id': move_line.location_dest_id.display_name or '',
                        'overall_qty': move_id.product_qty,
                        'overallscanned_qty': total_qty
                    })
            vals2['stock_move_line_data'] = scanned_data

            # Move to done automatically only for adhoc transfer
            if data_dict.get('is_adhoc_transfer', False):
                picking_id.app_action_confirm()
                if picking_id.state == 'confirmed':
                    picking_id.button_check_availability()
                if picking_id.state == 'assigned':
                    for move in picking_id.move_ids_without_package:
                        move.quantity_done = move.initial_demand
                    picking_id.with_context(skip_immediate=True, skip_backorder=True).button_validate()
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
            vals['qty'] = move_id.product_uom_qty
            vals['tracking'] = product_id.tracking
            vals['scanned_qty'] = move_id.quantity_done
            vals['package_type'] = move_id.package_type.name if move_id.package_type and move_id.package_type.name else ''
            vals['package_type_id'] = move_id.package_type.id if move_id.package_type else 0
            vals['qty_in_pack'] = move_id.qty_in_pack
            vals['qty_per_lot'] = move_id.qty_per_lot
            vals['product_uom_id'] = move_id.product_uom.id if move_id.product_uom else 0
            vals['product_uom'] = move_id.product_uom.name if move_id.product_uom else ''
            scanned_data = []
            # if product_id.tracking != 'none':
            for move_line in move_id.move_line_nosuggest_ids:
                scanned_data.append({'lot_name': move_line.lot_name or '', 'qty': move_line.qty_done, 'result_package_id': move_line.result_package_id.name if move_line.result_package_id else '', 'location_dest_id': move_line.location_dest_id.display_name or ''})
            vals['scanned_data'] = scanned_data
            data_list.append(vals)
        return data_list

    def app_action_assign(self, data_list):
        self.ensure_one()
        if self.state not in ['confirmed', 'partially_available', 'assigned']:
            picking_data = self.app_stock_picking_retrive_data()
            return {'error_message': False, 'stock_picking_data': picking_data}
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
        picking_data = self.app_stock_picking_retrive_data()
        return {'error_message': True, 'stock_picking_data': picking_data}

    def app_action_validate(self, data_list):
        self.ensure_one()
        if self.picking_type_code != 'incoming':
            self.app_action_assign(data_list)
        if self.state not in ['confirmed', 'partially_available', 'assigned']:
            picking_data = self.app_stock_picking_retrive_data()
            return {'error_message': False, 'stock_picking_data': picking_data}
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
        picking_data = self.app_stock_picking_retrive_data()
        return {'error_message': True, 'stock_picking_data': picking_data}

    def button_validate(self):
        context = dict(self.env.context or {})
        # self = self.with_context({'stock_picking_validate': True})
        res = super(StockPicking, self).button_validate()
        context.update({
            'stock_picking_validate': True
        })
        # Update stock move write date to refesh the app data
        product_ids = [line.product_id.id for line in self.move_lines]
        query = '''
            SELECT id FROM stock_move WHERE picking_status IN ('done', 'cancel', 'rejected') AND product_id IN %s
        '''
        self.env.cr.execute(query, [tuple(product_ids)])
        sql_result = self.env.cr.fetchall()
        move_ids = [item[0] for item in sql_result]
        current_datetime = datetime.now()
        if len(move_ids) == 1:
            self._cr.execute('''UPDATE stock_move SET write_date =%s WHERE id = %s''', (current_datetime, move_ids[0]))
            self._cr.commit()
        if not move_ids:
            pass
        else:
            self._cr.execute('''UPDATE stock_move SET write_date =%s WHERE id IN %s''', (current_datetime, tuple(move_ids)))
            self._cr.commit()
        return res

StockPicking()
