from odoo import tools
from odoo import _, api, fields, models

class ConsignmentAnalysis(models.AbstractModel):
    _name = 'consignment.analysis'
    _description = 'Consignment Analysis'

    product_id = fields.Many2one(
        comodel_name='product.template', string='Product')
    partner_id = fields.Many2one(
        comodel_name='res.partner', string='Customer')
    sale_id = fields.Many2one(
        comodel_name='sale.order', string='Sale Order')
    amount_total = fields.Float('Amount Total')
    date_order = fields.Date('Date')
    stock_sold = fields.Float('Quantity')
    so_count = fields.Integer('SO Count')
    qty = fields.Integer('Quantity')

    @property
    def _table_query(self):
        query =  '%s' % (self.query())
        return query

    def query(self):
        select_str ="""
                    SELECT  sol.id,
                            pt.id as product_id,
                            rp.id as partner_id,
                            so.id as sale_id,
                            so.amount_total as amount_total,
                            so.date_order,
							SUM(sol.product_uom_qty) as stock_sold,
                            COUNT(sol.id) as so_count,
                            SUM(sol.product_uom_qty) as qty
                    FROM sale_order_line as sol
                        left join sale_order as so ON sol.order_id = so.id
                        left join product_product as pp ON sol.product_id = pp.id
                        left join product_template as pt ON pp.product_tmpl_id = pt.id
                        left join res_partner as rp ON so.partner_id = rp.id
                    where so.sale_consign = True and so.state in ('sale','cancel')
					GROUP BY 
                            sol.id, 
                            pt.id, 
                            rp.id, 
                            so.id, 
                            so.amount_total, 
                            so.date_order
                        """
        return select_str
