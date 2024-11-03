from odoo import tools
from odoo import api, fields, models, _
# from datetime import datetime, date, timedelta

class ForecastQuantity(models.Model):
    _name = "forecast.quantity"
    _description = "Forecast Quantity"
    # _order = "schedule_date DESC"
    _auto = False

    schedule_date = fields.Datetime('Schedule Date')
    reference = fields.Many2one('stock.picking', 'Reference')
    product_id = fields.Many2one('product.product', 'Product')
    source_location = fields.Char('From')
    destination_location = fields.Char('To')
    forecast_qty = fields.Float('Forecast QTY')
    product_uom = fields.Char('Product Uom')
    state = fields.Selection([('1', 'IN'), 
                              ('2', 'OUT'),
                              ('3', 'OTHER')],
                              string='Status')
    
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """ SELECT 
                        a.id as id,
                        b.scheduled_date as schedule_date,
                        b.id as reference,
                        c.id as product_id,
                        e.complete_name as source_location,
                        f.complete_name as destination_location,
                        a.product_uom_qty as forecast_qty,
                        h.name as product_uom,
                        g.sequence_code as code,
                        CASE
                            when e.complete_name like '%Virtual%' then '1'
                            when f.complete_name like '%Virtual%' then '2'
                            when g.sequence_code = 'IN' then '1'
                            when g.sequence_code = 'OUT' then '2'
                            when g.sequence_code = 'INT' then '1'
                            when g.sequence_code = 'DS' then '3'
                        end state
                    FROM 
                        stock_move as a
                        left join stock_picking as b ON a.picking_id = b.id
                        left join product_product as c ON c.id = a.product_id
                        left join product_template as d ON d.id = c.product_tmpl_id
                        left join stock_location as e ON e.id = a.location_id
                        left join stock_location as f ON f.id = a.location_dest_id
                        left join stock_picking_type as g ON b.picking_type_id = g.id
                        left join uom_uom as h ON h.id = a.product_uom
                    WHERE 
                        a.state in ('partially_available', 'assigned')
                        and g.code in ('incoming', 'outgoing', 'internal')
                        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s
            )""" % (self._table, query))
    




