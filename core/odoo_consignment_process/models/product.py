# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    custom_is_consignment = fields.Boolean(
        string='Is Consignment',
        copy= False
    )
    purchase_order_line_id = fields.Many2one(
        'purchase.order.line',
        string="Purchase Line",
        readonly=True,
        copy=False,
    )
    custom_picking_id = fields.Many2one(
        'stock.picking',
        string="Consignment Picking",
        readonly=True,
        copy=False,
    ) #Old name picking_id

    sale_order_line_ids = fields.Many2many(
        'sale.order.line',
        string="Sale Order Line",
        readonly=True,
        copy=False,
    )
    pos_order_line_ids = fields.Many2many(
        'pos.order.line',
        string="POS Order Line",
        readonly=True,
        copy=False,
    )
    sale_state = fields.Selection(
        selection=[
            ('sold','Sold'),
            ('not_sold','Not Sold'),
        ],
        default="not_sold",
        string='Consignment Status',
        compute="_consignment_sale_state",
        readonly=False,
    )
    total_available_qty = fields.Float(
        string="Total Available Qty",
        compute="_consignment_total_available_qty",
        store=True,
    )
    purchase_qty = fields.Float(
        string="Purchase Qty",
        compute="_consignment_purchase",
        store=True,
        copy=False,
    )
    purchase_price = fields.Float(
        string="Purchase Price",
        readonly=True,
        copy=False,
    )
    purchase_price_total = fields.Float(
        string="Purchase Subtotal",
        compute="_consignment_purchase",
        store=True,
        copy=False,
    )
    sale_qty = fields.Float(
        string="Sale Qty",
        compute="_consignment_sale",
        store=True,
    )
    sale_price_total = fields.Float(
        string="Sale Subtotal",
        compute="_consignment_sale",
        store=True,
    )
    purchase_order_line_ids = fields.One2many(
        'purchase.order.line',
        'product_id',
        string="Purchase Line",
        readonly=True,
        copy=False,
    )

    @api.depends()
    def _consignment_sale_state(self):
        for rec in self:
            if rec.total_available_qty <= 0.0:
                rec.sale_state = 'sold'
            else:
                rec.sale_state = 'not_sold'

    @api.depends('sale_qty','purchase_qty')
    def _consignment_total_available_qty(self):
        for rec in self:
            rec.total_available_qty = rec.purchase_qty - rec.sale_qty

    @api.depends('sale_order_line_ids', 'sale_order_line_ids.order_id.is_consignment', 'sale_order_line_ids.state', 'sale_order_line_ids.product_uom_qty', 'pos_order_line_ids', 'pos_order_line_ids.custom_is_consignment', 'pos_order_line_ids.qty')
    def _consignment_sale(self):
        if not any(self.ids):
            self.sale_qty = 0.0
            self.sale_price_total = 0.0
            return

        query = """
        SELECT
            pp.id AS product_id,
            SUM(sol.price_subtotal) AS price_subtotal,
            SUM(sol.product_uom_qty) AS product_uom_qty
        FROM
            sale_order_line sol
        LEFT JOIN
            sale_order so
            ON (so.id = sol.order_id)
        LEFT JOIN
            product_product pp
            ON (pp.id = sol.product_id)
        WHERE
            pp.id IN %s
            AND so.is_consignment IS True
            AND so.state IN ('sale', 'done')
        GROUP BY
            pp.id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        sales = {o['product_id']: {
            'price_subtotal': o['price_subtotal'], 
            'product_uom_qty': o['product_uom_qty']
        } for o in self.env.cr.dictfetchall()}

        query = """
        SELECT
            pp.id AS product_id,
            SUM(pol.price_subtotal_incl) AS price_subtotal,
            SUM(pol.qty) AS product_uom_qty
        FROM
            pos_order_line pol
        LEFT JOIN
            pos_order po
            ON (po.id = pol.order_id)
        LEFT JOIN
            product_product pp
            ON (pp.id = pol.product_id)
        WHERE
            pp.id IN %s
            AND pol.custom_is_consignment IS True
            AND po.state IN ('paid', 'done', 'invoiced')
        GROUP BY
            pp.id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        pos = {o['product_id']: {
            'price_subtotal': o['price_subtotal'], 
            'product_uom_qty': o['product_uom_qty']
        } for o in self.env.cr.dictfetchall()}

        for rec in self:
            rec.sale_qty = sales.get(rec.id, {}).get('product_uom_qty', 0.0) + pos.get(rec.id, {}).get('product_uom_qty', 0.0)
            rec.sale_price_total = sales.get(rec.id, {}).get('price_subtotal', 0.0) + pos.get(rec.id, {}).get('price_subtotal', 0.0)

    @api.depends('purchase_order_line_ids','purchase_order_line_ids.state', 'purchase_order_line_ids.price_subtotal')
    def _consignment_purchase(self):
        if not any(self.ids):
            self.purchase_qty = 0.0
            self.purchase_price_total = 0.0
            return
        
        query = """
        SELECT
            pp.id AS product_id,
            SUM(pol.price_subtotal) AS price_subtotal,
            SUM(pol.product_qty) AS product_qty
        FROM
            purchase_order_line pol
        LEFT JOIN
            product_product pp
            ON (pp.id = pol.product_id)
        LEFT JOIN
            purchase_order po
            ON (po.id = pol.order_id)
        WHERE
            pp.id IN %s
            AND po.is_consignment IS True
            AND po.state IN ('purchase', 'done')
        GROUP BY
            pp.id
        """
        self.env.cr.execute(query, [tuple(self.ids)])
        result = {o['product_id']: {
            'price_subtotal': o['price_subtotal'], 
            'product_qty': o['product_qty']
        } for o in self.env.cr.dictfetchall()}
        for rec in self:
            rec.purchase_price_total = result.get(rec.id, {}).get('price_subtotal', 0.0)
            rec.purchase_qty = result.get(rec.id, {}).get('product_qty', 0.0)
