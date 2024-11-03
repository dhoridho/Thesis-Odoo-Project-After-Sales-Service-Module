# -*- coding: utf-8 -*-

import copy
from odoo import models, fields, api, _
from datetime import datetime, timedelta

class PosSyncSessionOrder(models.Model):
    _name = 'pos.sync.session.order'
    _description = 'Pos Sync Session Order'
    _rec_name = 'uid'

    uid = fields.Char('UID')
    data = fields.Text('Data')
    name = fields.Text('Name')
    database = fields.Char('Database')
    state = fields.Selection([('draft','Draft'), ('deleted','Deleted'), ('done','Done')], string='Status', default='draft')
    line_ids = fields.One2many('pos.sync.session.order.line', 'parent_id', string='Lines')
    pos_config_id = fields.Many2one('pos.config', string='POS Config')
    pos_session_id = fields.Many2one('pos.session', string='Session')

    def get_sequence_number(self):
        return int(self.env['ir.sequence'].next_by_code('pos.session.order.sequence'))

    def update_sync_state(self, pos_uid):
        domain = [('uid','=', pos_uid)]
        records = self.search(domain, limit=2)
        for rec in records:
            rec.write({ 'state': 'done' })
        return True

    def create_order_line(self, order, vals):
        Line = self.env['pos.sync.session.order.line']
        lines = vals['order']['lines']
        line_ids = [l.id for l in order.line_ids]
        pos_session_id = vals['pos_session_id']

        # Remove orderline
        for line in order.line_ids:
            line.unlink()

        values = {}
        for k, data in enumerate(lines):
            new_line = data[2]
            sync_line_id = new_line['sync_line_id']
            product_id = new_line['product_id']
            line_id = Line.create({
                'product_int': product_id,
                'qty': new_line['qty'],
                'name': new_line['full_product_name'],
                'data': data,
                'parent_id': order.id,
                'pos_session_id': pos_session_id,
            })
            sync_line_id = line_id.id
            order_line = copy.deepcopy(data)
            order_line_data = order_line[2]
            order_line_data['sync_line_id'] = line_id.id
            order_line_data['sync_line_create_date'] = line_id.create_date.strftime('%Y-%m-%d %H:%M:%S')
            line_id.write({'data': order_line })

        for line in order.line_ids:
            line_data = eval(line.data)[2]
            line_uid = False
            if 'uid' in line_data:
                line_uid = line_data['uid']
            if line_uid:
                values[line_uid] = line_data['sync_line_id']
        return values

 
    def new_order(self, vals):
        values = {}
        if 'sync_sequence_number' not in vals['order']:
            vals['order']['sync_sequence_number'] = self.get_sequence_number()

        order = self.search([('uid','=',vals['uid'])], limit=1)
        lines = vals['order']['lines']
        if not order:
            data = copy.deepcopy(vals['order'])
            data['lines'] = []
            order = self.create({
                'uid': vals['uid'],
                'database': vals['database'],
                'pos_config_id': vals['pos_config_id'],
                'pos_session_id': vals['pos_session_id'],
                'data': data,
                'name': vals['order']['name'],
            })
        if order:
            order.write({ 'data': vals['order'] })
            
        values['sync_line_ids'] = self.create_order_line(order, vals)
        return values

    def remove_order(self, vals):
        data_order = self.search([('uid','=',vals['uid'])], limit=1)
        if data_order:
            data_order.write({'state': 'deleted'})
        return { 'succees': True}

    def sync_orders(self, vals):
        domain = [('state','in', ['cancelled', 'done'])]
        if vals.get('removed_order_uids'):
            domain += [('uid','not in', vals['removed_order_uids'])]
        removed_orders = self.env['pos.sync.session.order'].search_read(domain, ['uid'])
        removed_order_uids = [o['uid'] for o in removed_orders]

        domain = [('state','in', ['draft'])]
        draft_orders = []
        orders = self.env['pos.sync.session.order'].search_read(domain, ['id', 'uid', 'data', 'state', 'line_ids','write_date'])
        if orders:
            domain = [('parent_id','in', [o['id'] for o in orders] )]
            lines = self.env['pos.sync.session.order.line'].search_read(domain, ['id', 'uid', 'data', 'parent_id','create_date'])

            for order in orders:
                value = copy.deepcopy(order)
                value['data'] = eval(value['data'])

                order_lines = []
                for line in lines:
                    if line['parent_id'][0] == order['id']:
                        order_lines += [eval(line['data'])]
                value['data']['lines'] = order_lines
                draft_orders += [value]

        return {
            'draft_orders': draft_orders,
            'removed_order_uids': removed_order_uids,
        }

    def sync_order(self, vals):
        values = []
        domain = [('uid','=', vals['uid'])]
        orders = self.env['pos.sync.session.order'].search_read(domain, ['id', 'uid', 'data', 'state', 'line_ids'])
        if orders:
            domain = [('parent_id','in', [o['id'] for o in orders] )]
            lines = self.env['pos.sync.session.order.line'].search_read(domain, ['id', 'uid', 'data', 'parent_id','create_date'])

            for order in orders:
                value = copy.deepcopy(order)
                value['data'] = eval(value['data'])

                order_lines = []
                for line in lines:
                    if line['parent_id'][0] == order['id']:
                        order_lines += [eval(line['data'])]
                value['data']['lines'] = order_lines
                values += [value]

        return values

    def remove_sync_data(self, session):
        # Remove sync session order data when Close Session
        domain = [('pos_config_id', '=', session.config_id.id)]
        records = self.search(domain)
        for rec in records:
            rec.unlink()
        return False

    def remove_sync_order_data(self):
        diff = 3 # 3 days ago
        date = (datetime.now() - timedelta(diff)).strftime('%Y-%m-%d 23:59:59')
        domain = [('state','in', ['deleted', 'done']), ('create_date','<=', date)]
        records = self.search(domain, limit=500)
        for rec in records:
            rec.unlink()
        return True
        

class PosSyncSessionOrderLine(models.Model):
    _name = 'pos.sync.session.order.line'
    _description = 'Pos Sync Session Order Line'
    _rec_name = 'uid'

    uid = fields.Char('UID')
    data = fields.Text('Data')
    name = fields.Text('Name')
    parent_id = fields.Many2one('pos.sync.session.order', string='Parent')
    product_int = fields.Integer('Product ID')
    qty = fields.Integer('Quantity')
    pos_session_id = fields.Many2one('pos.session', string='Session')