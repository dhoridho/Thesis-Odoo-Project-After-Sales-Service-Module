# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, tools, api, _


class ReportStockQuantityNew(models.Model):
    _name = 'report.stock.quantity.new'
    _auto = False
    _description = 'Stock Quantity Report'

    date = fields.Date(string='Date', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    state = fields.Selection([
        ('forecast', 'Forecasted Stock'),
        ('in', 'Forecasted Receipts'),
        ('out', 'Forecasted Deliveries'),
    ], string='State', readonly=True)
    product_qty = fields.Float(string='Quantity', readonly=True)
    move_ids = fields.One2many('stock.move', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_quantity_new')
        query = """
CREATE or REPLACE VIEW report_stock_quantity_new AS (
    SELECT
    MIN(id) as id,
    product_id,
    state,
    date,
    sum(product_qty) as product_qty,
    company_id,
    warehouse_id,
	row_num
FROM (SELECT
        m.id,
        m.product_id,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN 'out'
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN 'in'
        END AS state,
        m.date::date AS date,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN -product_qty
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN whs.id
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN whd.id
        END AS warehouse_id,
	 0 as row_num
    FROM
        stock_move m
    LEFT JOIN stock_location ls on (ls.id=m.location_id)
    LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    LEFT JOIN product_product pp on pp.id=m.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    WHERE
        pt.type = 'product' AND
        product_qty != 0 AND
        (whs.id IS NOT NULL OR whd.id IS NOT NULL) AND
        (whs.id IS NULL OR whd.id IS NULL OR whs.id != whd.id) AND
        date = now()::date and
        m.state NOT IN ('cancel', 'draft', 'done')
    UNION ALL
    SELECT
        -q.id as id,
        q.product_id,
        'forecast' as state,
        date_trunc('day', date.*)::date,
        q.quantity as product_qty,
        q.company_id,
        wh.id as warehouse_id,
	  row_number() OVER (PARTITION BY date_trunc('day', date) order by date, q.quantity desc) AS row_num
    FROM
        GENERATE_SERIES((now() at time zone 'utc')::date - interval '1month',
        (now() at time zone 'utc')::date + interval '1 month', '1 day'::interval) date,
        stock_quant q
    LEFT JOIN stock_location l on (l.id=q.location_id)
    LEFT JOIN stock_warehouse wh ON l.parent_path like concat('%/', wh.view_location_id, '/%')
    WHERE
        (l.usage = 'internal' AND wh.id IS NOT NULL) OR
        l.usage = 'transit'
    UNION ALL
    SELECT
        m.id,
        m.product_id,
        'forecast' as state,
        GENERATE_SERIES(
        CASE
            WHEN m.state = 'done' THEN (now() at time zone 'utc')::date - interval '1month'
            ELSE m.date::date
        END,
        CASE
            WHEN m.state != 'done' THEN (now() at time zone 'utc')::date + interval '1 month'
            ELSE m.date::date - interval '1 day'
        END, '1 day'::interval)::date date,
        CASE
            WHEN ((whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit') AND m.state = 'done' THEN product_qty
            WHEN ((whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit') AND m.state = 'done' THEN -product_qty
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN -product_qty
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN product_qty
        END AS product_qty,
        m.company_id,
        CASE
            WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN whs.id
            WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN whd.id
        END AS warehouse_id,
	  0 as row_num
    FROM
        stock_move m
    LEFT JOIN stock_location ls on (ls.id=m.location_id)
    LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    LEFT JOIN product_product pp on pp.id=m.product_id
    LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    WHERE
        pt.type = 'product' AND
        product_qty != 0 AND
        (whs.id IS NOT NULL OR whd.id IS NOT NULL) AND
        (whs.id IS NULL or whd.id IS NULL OR whs.id != whd.id) AND
        date = now()::date and
        m.state NOT IN ('cancel', 'draft')) AS forecast_qty
where row_num <= 5
GROUP BY product_id, state, date, company_id, warehouse_id,product_qty,row_num
ORDER BY date,row_num
);
"""
        # print('query',query)
        self.env.cr.execute(query)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=False):
        for i in range(len(domain)):
            if domain[i][0] == 'product_tmpl_id' and domain[i][1] in ('=', 'in'):
                tmpl = self.env['product.template'].browse(domain[i][2])
                # Avoid the subquery done for the related, the postgresql will plan better with the SQL view
                # and then improve a lot the performance for the forecasted report of the product template.
                domain[i] = ('product_id', 'in', tmpl.with_context(active_test=False).product_variant_ids.ids)
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    # def _query(self, with_clause='', fields={}, where='', groupby='',from_clause=''):
    #     with_ = ("WITH %s" % with_clause) if with_clause else ""
        
    #     select_ = """
    #         MIN(id) as id,
    #         product_id,
    #         state,
    #         date,
    #         sum(product_qty) as product_qty,
    #         company_id,
    #         warehouse_id
    #     FROM (SELECT
    #             m.id,
    #             m.product_id,
    #             CASE
    #                 WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN 'out'
    #                 WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN 'in'
    #             END AS state,
    #             m.date::date AS date,
    #             CASE
    #                 WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN -product_qty
    #                 WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN product_qty
    #             END AS product_qty,
    #             m.company_id,
    #             CASE
    #                 WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN whs.id
    #                 WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN whd.id
    #             END AS warehouse_id
    #         FROM
    #             stock_move m
    #         LEFT JOIN stock_location ls on (ls.id=m.location_id)
    #         LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    #         LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    #         LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    #         LEFT JOIN product_product pp on pp.id=m.product_id
    #         LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    #         WHERE
    #             pt.type = 'product' AND
    #             product_qty != 0 AND
    #             (whs.id IS NOT NULL OR whd.id IS NOT NULL) AND
    #             (whs.id IS NULL OR whd.id IS NULL OR whs.id != whd.id) AND
    #             m.state NOT IN ('cancel', 'draft', 'done')
    #         UNION ALL
    #         SELECT
    #             -q.id as id,
    #             q.product_id,
    #             'forecast' as state,
    #             date.*::date,
    #             q.quantity as product_qty,
    #             q.company_id,
    #             wh.id as warehouse_id
    #         FROM
    #             GENERATE_SERIES((now() at time zone 'utc')::date - interval '1 month',
    #             (now() at time zone 'utc')::date + interval '1 month', '1 day'::interval) date,
    #             stock_quant q
    #         LEFT JOIN stock_location l on (l.id=q.location_id)
    #         LEFT JOIN stock_warehouse wh ON l.parent_path like concat('%/', wh.view_location_id, '/%')
    #         WHERE
    #             (l.usage = 'internal' AND wh.id IS NOT NULL) OR
    #             l.usage = 'transit'
    #         UNION ALL
    #         SELECT
    #             m.id,
    #             m.product_id,
    #             'forecast' as state,
    #             GENERATE_SERIES(
    #             CASE
    #                 WHEN m.state = 'done' THEN (now() at time zone 'utc')::date - interval '1 month'
    #                 ELSE m.date::date
    #             END,
    #             CASE
    #                 WHEN m.state != 'done' THEN (now() at time zone 'utc')::date + interval '1 month'
    #                 ELSE m.date::date - interval '1 day'
    #             END, '1 day'::interval)::date date,
    #             CASE
    #                 WHEN ((whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit') AND m.state = 'done' THEN product_qty
    #                 WHEN ((whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit') AND m.state = 'done' THEN -product_qty
    #                 WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN -product_qty
    #                 WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN product_qty
    #             END AS product_qty,
    #             m.company_id,
    #             CASE
    #                 WHEN (whs.id IS NOT NULL AND whd.id IS NULL) OR ls.usage = 'transit' THEN whs.id
    #                 WHEN (whs.id IS NULL AND whd.id IS NOT NULL) OR ld.usage = 'transit' THEN whd.id
    #             END AS warehouse_id
    #         FROM
    #             stock_move m
    #         LEFT JOIN stock_location ls on (ls.id=m.location_id)
    #         LEFT JOIN stock_location ld on (ld.id=m.location_dest_id)
    #         LEFT JOIN stock_warehouse whs ON ls.parent_path like concat('%/', whs.view_location_id, '/%')
    #         LEFT JOIN stock_warehouse whd ON ld.parent_path like concat('%/', whd.view_location_id, '/%')
    #         LEFT JOIN product_product pp on pp.id=m.product_id
    #         LEFT JOIN product_template pt on pt.id=pp.product_tmpl_id
    #         WHERE
    #             pt.type = 'product' AND
    #             product_qty != 0 AND
    #             (whs.id IS NOT NULL OR whd.id IS NOT NULL) AND
    #             (whs.id IS NULL or whd.id IS NULL OR whs.id != whd.id) AND
    #             m.state NOT IN ('cancel', 'draft')) AS forecast_qty
    #     WHERE product_id IS NOT NULL AND product_qty IS NOT NULL
    #     GROUP BY product_id, state, date, company_id, warehouse_id ORDER BY product_qty DESC LIMIT 250
    #     """


    #     return '%s (SELECT %s)' % (with_, select_)

    # def init(self):
    #     # self._table = sale_report
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
