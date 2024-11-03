# -*- coding: utf-8 -*-

from odoo import tools
from odoo import fields, models


class MarginalReport(models.Model):
    _inherit = "marginal.report"

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """ SELECT pol.id AS id,
                        pp.product_display_name AS product_name,
                        rp.name AS consignor,
                        rp.name AS consignee,
                        pp.default_code AS product_code,
                        po.name AS reference,
                        spl.name as lot,
                        pol.qty_received - pol.sold_qty AS product_qty,
                        pol.price_unit * pol.qty_received AS purchase_price,
                        pol.qty_received AS purchase_qty,
                        pol.price_unit * pol.qty_received AS purchase_total,
                        so.name as sale_order_name,
                        po.effective_date as so_date,
                        pol.price_unit AS price_unit,
                        pol.sold_qty AS sale_qty,
                        pol.sold_price AS sale_price,
                        pol.sold_price - (pol.price_unit * pol.qty_received) AS margin,
                        po.branch_id AS branch_id,
                        CASE
                            WHEN pol.sold_qty = 0 then 'not_sold'
                            WHEN pol.product_qty = pol.sold_qty then 'sold'
                            WHEN pol.product_qty > pol.sold_qty then 'partial'
                        END state
                    FROM purchase_order_line AS pol
                        LEFT JOIN purchase_order po ON po.id = pol.order_id
                        LEFT JOIN product_product pp ON pp.id = pol.product_id
                        LEFT JOIN res_partner rp ON rp.id = po.partner_id
                        LEFT JOIN sale_order_line sol on sol.purchase_order_line_id = pol.id
                        LEFT JOIN sale_order so on so.id = sol.order_id
                        LEFT JOIN stock_picking sp ON sp.sale_id = sol.order_id
                        LEFT JOIN stock_move sm ON sm.picking_id = sp.id
                        LEFT JOIN stock_move_line sml ON sml.move_id = sm.id
                        LEFT JOIN stock_production_lot spl ON spl.id = sml.lot_id
                    WHERE po.is_consignment = True
                    GROUP BY pol.id,
                        pp.product_display_name,
                        rp.name,
                        spl.name,
                        pp.default_code,
                        po.name,
                        pol.product_qty,
                        pol.qty_received,
                        so.name,
                        po.effective_date,
                        pol.price_unit,
                        pol.sold_qty,
                        pol.sold_price,
                        po.branch_id"""
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))
