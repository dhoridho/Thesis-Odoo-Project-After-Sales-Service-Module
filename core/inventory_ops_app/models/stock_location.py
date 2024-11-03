# -*- coding: utf-8 -*-
from odoo import models
from datetime import datetime


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def get_stock_location_data(self):
        query = '''		       
            SELECT
               sl.id AS location_id,
               sl.complete_name AS location_name,
               sl.usage,
               sl.barcode As location_barcode,
               COALESCE(rb.id, 0) AS branch_id,
               COALESCE(rb.name, '') AS branch,
               COALESCE(sw.id, 0) AS warehouse_id,
               COALESCE(sw.name, '') AS warehouse
            FROM 
               stock_location as sl
               LEFT JOIN res_branch rb ON (sl.branch_id = rb.id)
               LEFT JOIN stock_warehouse sw ON (sl.warehouse_id = sw.id)
            WHERE
               sl.id != 0 AND sl.active != FALSE
            ORDER BY 
               location_id asc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.stock_location_date = datetime.now()
        return result

    def get_dynamic_stock_location_data(self):
        stock_location_datetime = self.env.user.stock_location_date or datetime.now()
        query = '''		       
            SELECT
               sl.id AS location_id,
               sl.complete_name AS location_name,
               sl.usage,
               sl.barcode As location_barcode,
               COALESCE(rb.id, 0) AS branch_id,
               COALESCE(rb.name, '') AS branch,
               COALESCE(sw.id, 0) AS warehouse_id,
               COALESCE(sw.name, '') AS warehouse
            FROM 
               stock_location as sl
               LEFT JOIN res_branch rb ON (sl.branch_id = rb.id)
               LEFT JOIN stock_warehouse sw ON (sl.warehouse_id = sw.id)
            WHERE
               sl.id != 0 AND sl.active != FALSE AND sl.write_date >= '%s' OR sl.create_date >= '%s'
            ORDER BY 
               location_id asc
        '''%(stock_location_datetime, stock_location_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.stock_location_date = datetime.now()
        return result