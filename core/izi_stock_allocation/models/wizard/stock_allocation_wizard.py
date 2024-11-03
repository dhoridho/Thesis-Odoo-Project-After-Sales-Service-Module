# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
        
class StockAllocationWizard(models.TransientModel):
    _name = 'stock.allocation.wizard'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    location_id = fields.Many2one('stock.location', string='Location', related='warehouse_id.lot_stock_id')
    product_ids = fields.Many2many('product.product', string='Products')

    def submit(self):
        action = self.env['ir.actions.actions']._for_xml_id('izi_stock_allocation.stock_allocation_balance_current_action')
        # action['domain'] = [('employee_id', '=', self.employee_id.id)]
        # action['context'] = {'default_employee_id': self.employee_id.id}

        # Delete All
        self.env.cr.execute('''
            DELETE FROM stock_allocation_balance_current;
        ''')

        product_query = ''
        if self.product_ids:
            product_query = ','.join([str(x.id) for x in self.product_ids])
            product_query = ' AND product_id IN (%s) ' % product_query
        # Current Balance
        query = '''
            SELECT 
                COALESCE(sum(qty), 0) as qty,
                product_id,
                sale_channel.code as channel_name
            FROM stock_allocation_move 
            LEFT JOIN sale_channel ON (sale_channel.id = stock_allocation_move.sale_channel_id)
            WHERE warehouse_id = %s %s
            GROUP BY 
                product_id,
                sale_channel.code;
        ''' % (self.warehouse_id.id, product_query)
        self.env.cr.execute(query)
        balance_data = self.env.cr.dictfetchall()
        total_allocated_by_product = {}
        for balance in balance_data:
            if balance['product_id'] not in total_allocated_by_product:
                total_allocated_by_product[balance['product_id']] = 0
            total_allocated_by_product[balance['product_id']] += balance['qty']
            # Write
            self.env.cr.execute('''
                INSERT INTO stock_allocation_balance_current (product_id, channel_name, qty)
                VALUES (%s, '%s', %s)
            ''' % (balance['product_id'], balance['channel_name'], balance['qty']))

        location_ids, location_str_ids = self.location_id.get_all_location_ids([], [])
        location_str = str(',').join(location_str_ids)
        product_query = ''
        if self.product_ids:
            product_query = ','.join([str(x.id) for x in self.product_ids])
            product_query = ' AND pp.id IN (%s) ' % product_query
        query_avl = '''
            SELECT 
                product_id,
                SUM(quantity - reserved_quantity) AS available_qty
            FROM stock_quant sq
            LEFT JOIN product_product pp ON (sq.product_id = pp.id)
            LEFT JOIN product_template pt ON (pp.product_tmpl_id = pt.id)
            WHERE location_id IN (%s) AND (pt.company_id IS NULL OR pt.company_id = %s) %s
            GROUP BY product_id;
        ''' % (location_str, self.env.company.id, product_query)
        self.env.cr.execute(query_avl)
        avl_data = self.env.cr.dictfetchall()
        for avl in avl_data:
            product_id = avl['product_id']
            total_stock = avl['available_qty']
            total_allocated = 0
            if product_id in total_allocated_by_product:
                total_allocated = total_allocated_by_product[product_id]
            total_unallocated = total_stock - total_allocated
            # Write
            # self.env.cr.execute('''
            #     INSERT INTO stock_allocation_balance_current (product_id, channel_name, qty)
            #     VALUES (%s, '%s', %s)
            # ''' % (product_id, ' TOTAL', total_stock))
            # self.env.cr.execute('''
            #     INSERT INTO stock_allocation_balance_current (product_id, channel_name, qty)
            #     VALUES (%s, '%s', %s)
            # ''' % (product_id, ' ALLO', total_allocated))
            self.env.cr.execute('''
                INSERT INTO stock_allocation_balance_current (product_id, channel_name, qty)
                VALUES (%s, '%s', %s)
            ''' % (product_id, '(UN)', total_unallocated))
        return action