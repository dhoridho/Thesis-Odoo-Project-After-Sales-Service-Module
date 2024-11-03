from odoo import models, api, fields, tools, _


class ItFinishedGoodMutation(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.finished.good.mutation'
    _description = 'Mutation of Finished Goods'
    _auto = False

    @api.depends_context('warehouse', 'date_from', 'date_to')
    @api.depends('product_id')
    def _compute_all(self):
        warehouse = self.env.context.get('warehouse', False)
        date_from = self.env.context.get('date_from', False)
        date_to = self.env.context.get('date_to', False)

        product_ids = self.mapped('product_id').with_context(warehouse=warehouse, location=False)
        quantities = self._get_quantities(product_ids, date_from=date_from, date_to=date_to)

        for record in self:
            product_id = record.product_id and record.product_id.id or False
            res = quantities.get(product_id, dict())
            record.first_balance = res.get('first_balance', 0.0)
            record.income = res.get('income', 0.0)
            record.outcome = res.get('outcome', 0.0)
            record.adjustment = res.get('adjustment', 0.0)
            record.last_balance = res.get('last_balance', 0.0)
            record.stock_opname = res.get('stock_opname', 0.0)
            record.difference = res.get('difference', 0.0)
            record.description = res.get('description', False)

    sequence = fields.Integer(string='No')
    product_id = fields.Many2one('product.product', string='Product')

    uom_id = fields.Many2one('uom.uom', string='UoM', related='product_id.uom_id')
    product_code = fields.Char(string='Product Code', related='product_id.default_code')
    
    first_balance = fields.Float(string='Initial Balance', compute=_compute_all)
    income = fields.Float(string='Income', compute=_compute_all)
    outcome= fields.Float(string='Outcome', compute=_compute_all)
    adjustment = fields.Float(string='Adjustment', compute=_compute_all)
    last_balance = fields.Float(string='Ending Balance', compute=_compute_all)
    stock_opname = fields.Float(string='Stock Opname', compute=_compute_all)
    difference = fields.Float(string='Difference', compute=_compute_all)
    description = fields.Char(string='Description', compute=_compute_all)

    @api.model
    def _get_quantities(self, product_ids, date_from=None, date_to=None):
        res = product_ids._compute_quantities_dict_custom(from_date=date_from, to_date=date_to)
        stock_inventory_line = self.env['stock.inventory.line']

        result = dict()
        for product_id in product_ids:
            first_balance = res[product_id.id]['first_balance']
            income = res[product_id.id]['income']
            outcome = res[product_id.id]['outcome']
            last_balance = first_balance + income - outcome
            stock_opname = sum(stock_inventory_line.search([('product_id', '=', product_id.id)]).mapped('product_qty'))
            adjustment = stock_opname - first_balance - income
            difference = abs(adjustment)
            if adjustment > 0.0:
                description = 'Positive Different'
            elif adjustment < 0.0:
                description = 'Negative Different'
            else:
                description = 'Matching'
            
            result[product_id.id] = {
                'first_balance': first_balance,
                'income': income,
                'outcome': outcome,
                'adjustment': adjustment,
                'last_balance': last_balance,
                'stock_opname': stock_opname,
                'difference': difference,
                'description': description
            }
        return result


    @api.model
    def _query(self):
        return """
        SELECT
            sm.product_id as id,
            sm.product_id as product_id,
            ROW_NUMBER() OVER (ORDER BY sm.product_id) AS sequence
        FROM
            stock_move sm
        LEFT JOIN
            product_product pp
            ON (pp.id = sm.product_id)
        LEFT JOIN
            product_template pt
            ON (pt.id = pp.product_tmpl_id)
        LEFT JOIN
            stock_warehouse sw
            ON (sw.id = sm.warehouse_id)
        WHERE
            sw.is_it_inventory_warehouse = True AND pt.manuf_type = 'type_fg'
        GROUP BY
            sm.product_id
        ORDER BY
            sm.product_id
        """

    @api.model
    def get_report_name(self):
        return _('Mutation of Finished Goods')

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'product_code', 'product_id', 'uom_id', 'first_balance', 'income', 
            'outcome', 'adjustment', 'last_balance', 'stock_opname', 'difference', 'description'
        ]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
