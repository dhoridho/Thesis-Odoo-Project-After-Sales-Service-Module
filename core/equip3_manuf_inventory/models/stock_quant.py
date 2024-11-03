from odoo import models, fields, api, _


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _gather_product(self, product_id):
        self.env['stock.quant'].flush(['location_id', 'owner_id', 'package_id', 'lot_id', 'product_id'])
        self.env['product.product'].flush(['virtual_available'])

        domain = [('product_id', '=', product_id.id), ('location_id.usage', '=', 'internal')]

        # Copy code of _search for special NULLS FIRST/LAST order
        self.check_access_rights('read')
        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()
        # No uniquify list necessary as auto_join is not applied anyways...
        quants = self.browse([x[0] for x in res])
        quants = quants.sorted(lambda q: not q.lot_id)
        return quants
