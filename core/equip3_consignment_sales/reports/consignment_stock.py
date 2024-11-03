from odoo import tools
from odoo import _, api, fields, models

class ConsignmentStock(models.AbstractModel):
    _name = 'consignment.stock'
    _description = 'Consignment Stock'

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse', string='Warehouse')
    location_id = fields.Many2one(
        comodel_name='stock.location', string='Location')
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product')
    quantity = fields.Integer('Quantity')

    @property
    def _table_query(self):
        query =  '%s' % (self.query())
        return query

    def query(self):
        select_str ="""
                    SELECT
                       sq.id,
                       sl.id as location_id,
                       sw.id as warehouse_id,
                       pp.id as product_id,
                       sq.quantity as quantity
                    FROM
                        stock_quant as sq
                            left join product_product as pp on sq.product_id = pp.id
                            left join product_template as pt on pp.product_tmpl_id = pt.id
                            left join stock_location as sl on sq.location_id = sl.id
                            left join stock_warehouse as sw on sl.warehouse_id = sw.id
                    WHERE
                        sw.is_consignment_warehouse = True
                        """
        return select_str
