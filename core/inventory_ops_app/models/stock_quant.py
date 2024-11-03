# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools
from datetime import datetime


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def update_write_time(self, product_ids):
        query = '''
            SELECT id FROM stock_move WHERE picking_status IN ('done', 'cancel', 'rejected') AND product_id IN (%s)
        '''%(tuple(product_ids))
        self.env.cr.execute(query)
        result = self.env.cr.fetchall()
        move_ids = [item[0] for item in result]
        current_datetime = datetime.now()
        if len(move_ids) == 1:
            self._cr.execute('''UPDATE stock_move SET write_date =%s WHERE id = %s''', (current_datetime, move_ids[0]))
            self._cr.commit()
        else:
            self._cr.execute('''UPDATE stock_move SET write_date =%s WHERE id IN %s''', (current_datetime, tuple(move_ids)))
            self._cr.commit()
        return True

    @api.model
    def create(self, vals):
        quant = super(StockQuant, self).create(vals)
        if not self.env.context.get('stock_picking_validate') and vals.get('product_id'):
            self.update_write_time([vals.get('product_id')])
        return quant

    def write(self, vals):
        quant = super(StockQuant, self).write(vals)
        product_ids = self.mapped('product_id').ids or []
        if not self.env.context.get('stock_picking_validate') and product_ids:
            self.update_write_time(product_ids)
        return quant

    def unlink(self):
        product_ids = self.mapped('product_id').ids or []
        if not self.env.context.get('stock_picking_validate') and product_ids:
            self.update_write_time(product_ids)
        return super(StockQuant, self).unlink()


StockQuant()