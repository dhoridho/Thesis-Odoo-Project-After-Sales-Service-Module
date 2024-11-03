from odoo import _, api, fields, models
from odoo.exceptions import Warning
from odoo.exceptions import UserError


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    scrap_sale_price = fields.Float(string="Scrap Sale Price")
    is_low_stock = fields.Boolean(string="Is Low Stock")




class StockMove(models.Model):
    _inherit = "stock.move"

    def _account_entry_move(self, qty, description, svl_id, cost):
        context = dict(self.env.context) or {}
        if context.get('is_scrap') or context.get('default_is_product_usage'):
            pass
        else:
            return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)

    def _get_src_account(self, accounts_data):
        context = dict(self.env.context) or {}
        if 'is_inv_adj_acc' in context and self.inventory_id and self.inventory_id.adjustment_account_id:
            return self.inventory_id.adjustment_account_id.id
        return super(StockMove, self)._get_src_account(accounts_data)

    def _get_dest_account(self, accounts_data):
        context = dict(self.env.context) or {}
        if 'is_inv_adj_acc' in context and self.inventory_id and self.inventory_id.adjustment_account_id:
            return self.inventory_id.adjustment_account_id.id
        return super(StockMove, self)._get_dest_account(accounts_data)

    @api.model
    def _get_freezed_inventories_where(self, inventory_ids=None):
        where_clause, query_params = super(StockMove, self)._get_freezed_inventories_where(inventory_ids=inventory_ids)
        where_clause += ['si.freeze_inventory IS True']
        return where_clause, query_params

    @api.model
    def _get_freezed_scraps(self, scrap_request_ids=None):
        where_clause = ["ssr.state = 'validating'"]
        query_params = []

        if scrap_request_ids:
            where_clause += ['ssr.id NOT IN %s']
            query_params += [tuple(scrap_request_ids)]

        where_clause = ' AND '.join(where_clause)
        
        self.env.cr.execute("""
        SELECT
            ss.location_id AS location_id,
            STRING_AGG(DISTINCT(ssr.{field_name})::character varying, ',') AS scrap_names
        FROM
            stock_scrap ss
        LEFT JOIN
            stock_scrap_request ssr
            ON (ss.scrap_id = ssr.id)
        WHERE
            {where_clause}
        GROUP BY
            ss.location_id
        """.format(where_clause=where_clause, field_name=self.env['stock.scrap.request']._rec_name), query_params)

        return {o[0]: ', '.join((o[1] or '').split(',')) for o in self.env.cr.fetchall()}

    def _get_freezed_locations(self):
        res = super(StockMove, self)._get_freezed_locations()
        scrap_request_ids = self.mapped('scrap_ids').mapped('scrap_id').ids
        freezed_scraps = self._get_freezed_scraps(scrap_request_ids)
        for location_id, scrap_source in freezed_scraps.items():
            res[location_id] = ','.join(o for o in [res.get(location_id), scrap_source] if o)
        return res
