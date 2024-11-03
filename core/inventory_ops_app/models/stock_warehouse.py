# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    def get_stock_warehouse_data(self):
        query = '''
            SELECT
               sw.id AS warehouse_id,
               sw.name AS warehouse,
               COALESCE(rb.id, 0) AS branch_id,
               COALESCE(rb.name, '') AS branch
            FROM
               stock_warehouse as sw
               LEFT JOIN res_branch rb ON (sw.branch_id = rb.id)
            WHERE
               sw.id != 0 AND sw.active != FALSE
            ORDER BY 
                warehouse_id asc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.stock_warehouse_date = datetime.now()
        return result

    def get_dynamic_stock_warehouse_data(self):
        stock_warehouse_dt = self.env.user.stock_warehouse_date or datetime.now()
        query = '''
            SELECT
               sw.id AS warehouse_id,
               sw.name AS warehouse,
               COALESCE(rb.id, 0) AS branch_id,
               COALESCE(rb.name, '') AS branch
            FROM
               stock_warehouse as sw
               LEFT JOIN res_branch rb ON (sw.branch_id = rb.id)
            WHERE
               sw.id != 0 AND sw.active != FALSE AND sw.write_date >= '%s' OR sw.create_date >= '%s'
            ORDER BY 
                warehouse_id asc
        '''%(stock_warehouse_dt, stock_warehouse_dt)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.stock_warehouse_date = datetime.now()
        return result
