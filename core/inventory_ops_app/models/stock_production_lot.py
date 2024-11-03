# -*- coding: utf-8 -*-
from odoo import _, fields, models, api
from datetime import datetime


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    def get_stock_production_lot_data(self):
        query = '''
        SELECT
           spl.id as lot_id,
           spl.product_id as product_id,
           spl.name as lot_name,
           spl.company_id as company_id
        FROM
           stock_production_lot as spl
        WHERE
           spl.id != 0
        ORDER BY
           lot_id desc
        '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.stock_production_lot_date = datetime.now()
        return result

    def get_dynamic_stock_production_lot_data(self):
        stock_production_lot_datetime = self.env.user.stock_production_lot_date or datetime.now()
        query = '''
        SELECT
           spl.id as lot_id,
           spl.product_id as product_id,
           spl.name as lot_name,
           spl.company_id as company_id
        FROM
           stock_production_lot as spl
        WHERE
           spl.id != 0 AND spl.write_date >= '%s' OR spl.create_date >= '%s'
        ORDER BY
           lot_id desc
        '''%(stock_production_lot_datetime, stock_production_lot_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.stock_production_lot_date = datetime.now()
        return result