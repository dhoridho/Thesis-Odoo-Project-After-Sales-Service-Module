# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
import requests
import json
import math

from email.policy import default
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class StockAllocationMove(models.Model):
    _name = 'stock.allocation.move'

    date = fields.Datetime('Date', default=fields.Datetime.now)
    product_id = fields.Many2one('product.product', 'Product')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    location_id = fields.Many2one('stock.location', 'Location', related='warehouse_id.lot_stock_id', store=True)
    sale_channel_id = fields.Many2one('sale.channel', 'Channel')
    qty = fields.Integer('Quantity')
    move_id = fields.Many2one('stock.move', string='Move Reference')
    picking_id = fields.Many2one('stock.picking', string='Transfer Reference')
    sale_line_id = fields.Many2one('sale.order.line', string='Sales Line Reference')
    sale_id = fields.Many2one('sale.order', string='Sales Order Reference')
    form_id = fields.Many2one('stock.allocation.form', string='Form')
    balance_id = fields.Many2one('stock.allocation.balance', string='Balance')

class StockAllocationBalance(models.Model):
    _name = 'stock.allocation.balance'
    _order = 'warehouse_id, date desc'

    name = fields.Char('Name', store=True, compute='_compute_name')
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    location_id = fields.Many2one('stock.location', 'Location', related='warehouse_id.lot_stock_id', store=True)
    method = fields.Selection([('unallocated', 'Allocate Unallocated Stock'), ('all', 'Rebalance All Stock')], default='unallocated', string='Method')
    all = fields.Boolean('All Products & Channels', default=False)
    sync = fields.Boolean('Sync', default=True)
    line_ids = fields.One2many('stock.allocation.balance.line', 'balance_id', string='Balance Lines')
    stock_line_ids = fields.One2many('stock.allocation.stock.line', 'balance_id', string='Stock Lines')
    state = fields.Selection([
        ('new', 'New'),
        ('start', 'Started'),
        ('confirm', 'Confirmed'),
    ], default='new', string='Status')
    adjustment_move_ids = fields.One2many('stock.allocation.move', 'balance_id', string='Adjustment Moves')

    @api.depends('date')
    def _compute_name(self):
        for record in self:
            record.name = record.date.strftime('%Y-%m-%d %H:%M:%S')
    
    def action_adjustment(self):
        self.ensure_one()
        self.state = 'adjustment'
    
    def mp_sync_allocation(self):
        self.ensure_one()
    
    def action_confirm(self, force=False):
        self.ensure_one()

        # Check Changes
        if not force:
            if not self.check_balance():
                return False

        # Check Stock Line
        for stock_line in self.stock_line_ids:
            if stock_line.unallocated < 0:
                raise UserError('Cannot allocate more than stock!')

        # Create Move
        AllocationMove = self.env['stock.allocation.move']

        json_channel_stock_allocation = {}

        for line in self.line_ids:
            diff_qty = line.end_qty - line.qty
            if diff_qty != 0:
                if self.sync:
                    if line.sale_channel_id.platform == 'mp':
                        # Push Stock to Marketplace
                        if 'mp' not in json_channel_stock_allocation:
                            json_channel_stock_allocation['mp'] = {}
                        if self.env['ir.module.module'].sudo().search([('name', '=', 'izi_marketplace'), ('state', '=', 'installed')]):
                            map_line_ids = line.product_id.map_line_ids
                            marketplace = line.sale_channel_id.mp_account_id.marketplace
                            wiz_lines = []
                            for map_line_id in map_line_ids:
                                if map_line_id.mp_account_id.id == line.sale_channel_id.mp_account_id.id:
                                    if map_line_id.default_code == line.product_id.default_code:
                                        if marketplace not in json_channel_stock_allocation['mp']:
                                            json_channel_stock_allocation['mp'][marketplace] = {}
                                        if map_line_id.mp_product_id:
                                            wiz_line = (0, 0, {
                                                'mp_product_id': 'mp.product,%s' % (map_line_id.mp_product_id.id),
                                                'stock': line.end_qty,
                                            })
                                            if line.sale_channel_id.mp_account_id.id not in json_channel_stock_allocation['mp'][marketplace]:
                                                json_channel_stock_allocation['mp'][marketplace][line.sale_channel_id.mp_account_id.id] = [wiz_line]
                                            else:
                                                json_channel_stock_allocation['mp'][marketplace][line.sale_channel_id.mp_account_id.id].append(wiz_line)
                                            # wiz_lines.append(wiz_line)
                                        if map_line_id.mp_product_variant_id:
                                            wiz_line = (0, 0, {
                                                'mp_product_id': 'mp.product.variant,%s' % (map_line_id.mp_product_variant_id.id),
                                                'stock': line.end_qty,
                                            })
                                            if line.sale_channel_id.mp_account_id.id not in json_channel_stock_allocation['mp'][marketplace]:
                                                json_channel_stock_allocation['mp'][marketplace][line.sale_channel_id.mp_account_id.id] = [wiz_line]
                                            else:
                                                json_channel_stock_allocation['mp'][marketplace][line.sale_channel_id.mp_account_id.id].append(wiz_line)
                                        break
                                        # wiz_lines.append(wiz_line)
                values = {
                    'date': self.date,
                    'product_id': line.product_id.id,
                    'warehouse_id': self.warehouse_id.id,
                    'location_id': self.location_id.id,
                    'sale_channel_id': line.sale_channel_id.id,
                    'balance_id': self.id,
                    'qty': math.floor(diff_qty),
                }
                AllocationMove.create(values)
        for channel in json_channel_stock_allocation:
            if channel == 'mp':
                for marketplace in json_channel_stock_allocation['mp']:
                    wiz = self.env['wiz.mp.product.update'].create({
                            'mp_account_ids': [(6, 0, [mp for mp in json_channel_stock_allocation['mp'][marketplace]])],
                            'line_ids': [json_channel_stock_allocation['mp'][marketplace][line] for line in json_channel_stock_allocation['mp'][marketplace]][0]
                        })
                    wiz.update()
        self.state = 'confirm'

    def check_balance(self):
        self.ensure_one()
        qty_changed = False

        # Current Balance Line
        self.env.cr.execute('''
            SELECT id, product_id, sale_channel_id, qty, add_qty, end_qty
            FROM stock_allocation_balance_line
            WHERE balance_id = %s
        ''' % (self.id))
        balance_line_data = self.env.cr.dictfetchall()
        balance_line_by_product_by_channel = {}
        for balance_line in balance_line_data:
            product_id = balance_line['product_id']
            sale_channel_id = balance_line['sale_channel_id']
            if product_id not in balance_line_by_product_by_channel:
                balance_line_by_product_by_channel[product_id] = {}
            if sale_channel_id not in balance_line_by_product_by_channel[product_id]:
                balance_line_by_product_by_channel[product_id][sale_channel_id] = {
                    'id': balance_line['id'],
                    'qty': balance_line['qty'] or 0,
                    'add_qty': balance_line['add_qty'] or 0,
                    'end_qty': balance_line['end_qty'] or 0,
                }
        # Current Balance From Current Move
        query = '''
            SELECT 
                COALESCE(sum(qty), 0) as qty,
                product_id,
                sale_channel_id
            FROM stock_allocation_move 
            LEFT JOIN sale_channel ON (sale_channel.id = stock_allocation_move.sale_channel_id)
            WHERE location_id = %s
                AND sale_channel_id IS NOT NULL
            GROUP BY 
                product_id,
                sale_channel_id;
        ''' % (self.location_id.id)
        self.env.cr.execute(query)
        balance_data = self.env.cr.dictfetchall()
        for balance in balance_data:
            product_id = balance['product_id']
            sale_channel_id = balance['sale_channel_id']
            if product_id in balance_line_by_product_by_channel and sale_channel_id in balance_line_by_product_by_channel[product_id]:
                last_qty = balance_line_by_product_by_channel[product_id][sale_channel_id]['qty']
                last_add_qty = balance_line_by_product_by_channel[product_id][sale_channel_id]['add_qty']
                balance_line_id = balance_line_by_product_by_channel[product_id][sale_channel_id]['id']
                # Check If Qty Different, Then Update
                if math.floor(last_qty) != math.floor(balance['qty']):
                    qty_changed = True
                    new_qty = balance['qty']
                    new_add_qty = last_add_qty
                    new_end_qty = new_qty + new_add_qty
                    self.env.cr.execute('''
                        UPDATE stock_allocation_balance_line
                        SET qty = %s, add_qty = %s, end_qty = %s
                        WHERE balance_id = %s
                        AND product_id = %s
                        AND sale_channel_id = %s
                    ''' % (new_qty, new_add_qty, new_end_qty, self.id, product_id, sale_channel_id))
        self.state = 'start'
        for stock_line in self.stock_line_ids:
            stock_line._compute_allocated()
        if qty_changed:
            return False
            # raise UserError('Allocation Balance has changed during the rebalance process. The system has updated the balance. Please check again before confirm.')
        return True

    def start_rebalance(self):
        self.ensure_one()
        # Delete Balance Line
        self.line_ids.unlink()
        self.stock_line_ids.unlink()
        self.date = fields.Datetime.now()

        # Current Balance From Current Move
        query = '''
            SELECT 
                COALESCE(sum(qty), 0) as qty,
                product_id,
                sale_channel_id
            FROM stock_allocation_move 
            LEFT JOIN sale_channel ON (sale_channel.id = stock_allocation_move.sale_channel_id)
            WHERE "date" <= '%s'
                AND location_id = %s
            GROUP BY 
                product_id,
                sale_channel_id;
        ''' % (self.date.strftime('%Y-%m-%d %H:%M:%S'), self.location_id.id)
        self.env.cr.execute(query)
        balance_data = self.env.cr.dictfetchall()
        balance_by_product_by_channel = {}
        total_allocated_by_product = {}
        for balance in balance_data:
            if balance['product_id'] not in balance_by_product_by_channel:
                balance_by_product_by_channel[balance['product_id']] = {}
            balance_by_product_by_channel[balance['product_id']][balance['sale_channel_id']] = balance['qty']
            # Total Allocated
            if balance['product_id'] not in total_allocated_by_product:
                total_allocated_by_product[balance['product_id']] = 0
            total_allocated_by_product[balance['product_id']] += balance['qty']
        # Forecast
        # Distribute Based on Product Forecast, Then Allocation Percentage
        date_start = date.today().replace(day=1)
        date_end = date.today().replace(day=1) + relativedelta(months=1)
        date_start = date_start.strftime('%Y-%m-%d 00:00:00')
        date_end = date_end.strftime('%Y-%m-%d 00:00:00')

        # Get Available Stock
        # Get All Child Location Ids
        BalanceLine = self.env['stock.allocation.balance.line']
        head_channels = self.env['sale.channel'].search([('parent_id', '=', False)])
        location_ids, location_str_ids = self.location_id.get_all_location_ids([], [])
        location_str = str(',').join(location_str_ids)
        query_avl = '''
            SELECT 
                product_id,
                SUM(quantity - reserved_quantity) AS available_qty
            FROM stock_quant sq
            LEFT JOIN product_product pp ON (sq.product_id = pp.id)
            LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
            WHERE location_id IN (%s) AND (pt.company_id IS NULL OR pt.company_id = %s)
            GROUP BY product_id;
        ''' % (location_str, self.env.company.id)
        self.env.cr.execute(query_avl)
        avl_data = self.env.cr.dictfetchall()
        avl_by_product = {}
        index = 0
        for avl in avl_data:
            index += 1
            avl_by_product[avl['product_id']] = avl['available_qty']
            product_id = avl['product_id']
            total_stock = avl['available_qty']
            # Create Stock Line
            self.env.cr.execute('''
                INSERT INTO stock_allocation_stock_line (balance_id, product_id, total_stock)
                VALUES (%s, %s, %s) RETURNING id
            ''' % (self.id, product_id, avl['available_qty']))
            stock_line_id = self.env.cr.fetchone()[0]
            total_allocated_after_rebalance = 0
            total_allocated = 0
            if product_id in total_allocated_by_product:
                total_allocated = total_allocated_by_product[product_id]
            total_unallocated = total_stock - total_allocated
            # Iterate Channels
            for head_channel in head_channels:
                # Calculate Ending Balance For Head Channel
                head_channel_begin_qty = 0
                head_channel_end_qty = 0
                head_channel_add_qty = 0
                if self.method == 'all':
                    head_channel_end_qty = math.floor((head_channel.allocation_percentage / head_channel.total_allocation_percentage) * total_stock)
                elif self.method == 'unallocated':
                    head_channel_add_qty = math.floor((head_channel.allocation_percentage / head_channel.total_allocation_percentage) * total_unallocated)
                if product_id in balance_by_product_by_channel and head_channel.id in balance_by_product_by_channel[product_id]:
                    head_channel_begin_qty = balance_by_product_by_channel[product_id][head_channel.id]
                # 
                # Create Balance Line in Child Channels
                child_channels = head_channel.get_last_child_channels()
                if child_channels:
                    for child_channel in child_channels:
                        # Get Beginning Balance
                        begin_qty = 0
                        if product_id in balance_by_product_by_channel and child_channel['id'] in balance_by_product_by_channel[product_id]:
                            begin_qty = balance_by_product_by_channel[product_id][child_channel['id']]
                        # Get Calculated Ending Balance
                        add_qty = 0
                        end_qty = 0
                        if child_channel['total_allocation_percentage']:
                            if self.method == 'all':
                                end_qty = math.floor((child_channel['allocation_percentage'] / child_channel['total_allocation_percentage']) * head_channel_end_qty)
                                add_qty =  end_qty - begin_qty
                            elif self.method == 'unallocated':
                                add_qty = math.floor((child_channel['allocation_percentage'] / child_channel['total_allocation_percentage']) * head_channel_add_qty)
                                end_qty = begin_qty + add_qty
                        # Create Balance Line
                        if self.all or (begin_qty or end_qty):
                            self.env.cr.execute('''
                                INSERT INTO stock_allocation_balance_line (balance_id, stock_line_id, product_id, sale_channel_id, qty, add_qty, end_qty)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ''' % (self.id, stock_line_id, product_id, child_channel['id'], begin_qty, add_qty, end_qty))
                            total_allocated_after_rebalance += end_qty
                else:
                    # Get Beginning Balance
                    if self.method == 'all':
                        head_channel_add_qty = head_channel_end_qty - head_channel_begin_qty
                    elif self.method == 'unallocated':
                        head_channel_end_qty = head_channel_begin_qty + head_channel_add_qty
                    if self.all or (head_channel_begin_qty or head_channel_end_qty):
                        self.env.cr.execute('''
                            INSERT INTO stock_allocation_balance_line (balance_id, stock_line_id, product_id, sale_channel_id, qty, add_qty, end_qty)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''' % (self.id, stock_line_id, product_id, head_channel.id, head_channel_begin_qty, head_channel_add_qty, head_channel_end_qty))
                        total_allocated_after_rebalance += head_channel_end_qty
            
            self.env.cr.execute('''
                UPDATE stock_allocation_stock_line
                SET allocated = %s,
                unallocated = %s
                WHERE balance_id = %s
                AND product_id = %s
            ''' % (total_allocated_after_rebalance, (total_stock - total_allocated_after_rebalance), self.id, product_id))
        self.state = 'start'
        
    @api.model
    def auto_allocate(self, method='unallocated'):
        company_id = self.env.company.id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        balance = self.create({
            'warehouse_id': warehouse.id,
            'method': method,
        })
        try:
            balance.start_rebalance()
            self.env.cr.commit()
        except Exception as e:
            raise UserError(str(e))
        balance.action_confirm(force=True)

class StockAllocationStockLine(models.Model):
    _name = 'stock.allocation.stock.line'
    _order = 'product_id asc, allocated desc'

    balance_id = fields.Many2one('stock.allocation.balance', 'Balance', ondelete='cascade')
    balance_line_ids = fields.One2many('stock.allocation.balance.line', 'stock_line_id', string='Balance Lines')
    # date = fields.Datetime('Date', related='balance_id.date', store=True)
    # warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', related='balance_id.warehouse_id', store=True)
    # location_id = fields.Many2one('stock.location', 'Location', related='balance_id.location_id', store=True)
    product_id = fields.Many2one('product.product', 'Product')
    total_stock = fields.Integer('Total Stock')
    allocated = fields.Integer('Allocated', compute='_compute_allocated', store=True)
    unallocated = fields.Integer('Unallocated', compute='_compute_allocated', store=True)

    @api.depends('balance_line_ids.end_qty')
    def _compute_allocated(self):
        for record in self:
            record.allocated = 0
            for balance_line in record.balance_line_ids:
                record.allocated += balance_line.end_qty
            record.unallocated = record.total_stock - record.allocated

class StockAllocationBalanceLine(models.Model):
    _name = 'stock.allocation.balance.line'
    _order = 'product_id asc, sale_channel_id asc'

    balance_id = fields.Many2one('stock.allocation.balance', 'Balance', ondelete='cascade')
    stock_line_id = fields.Many2one('stock.allocation.stock.line', 'Stock Line')
    # date = fields.Datetime('Date', related='balance_id.date', store=False)
    # warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', related='balance_id.warehouse_id', store=False)
    # location_id = fields.Many2one('stock.location', 'Location', related='balance_id.location_id', store=False)
    product_id = fields.Many2one('product.product', 'Product')
    sale_channel_id = fields.Many2one('sale.channel', 'Channel', domain=[('child_ids', '=', False)])
    add_qty = fields.Integer('Add')
    qty = fields.Integer('Beginning')
    end_qty = fields.Integer('Ending')
    sync = fields.Boolean('Synced')
    sync_datetime = fields.Datetime('Sync Date')

    _sql_constraints = [
        ("balance_product_channel_uniq", "unique(balance_id,product_id,sale_channel_id)",
         "Product and Sales Channel must be unique")
    ]

    @api.onchange('add_qty')
    def onchange_add(self):
        self.end_qty = self.qty + self.add_qty

    @api.onchange('end_qty')
    def onchange_end(self):
        self.add_qty = self.end_qty - self.qty

class StockAllocationBalanceCurrent(models.Model):
    _name = 'stock.allocation.balance.current'
    _order = 'product_id asc'

    product_id = fields.Many2one('product.product', 'Product')
    channel_name = fields.Char('Channel')
    qty = fields.Integer('Qty')

