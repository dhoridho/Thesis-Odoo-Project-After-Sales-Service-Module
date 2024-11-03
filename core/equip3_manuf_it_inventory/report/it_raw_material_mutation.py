from odoo import models, api, fields, tools, _
from datetime import datetime, timedelta, time


class ItRawMaterialMutation(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.raw.material.mutation'
    _description = 'Mutation of Raw Materials'
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
            record.stock_on_hand = res.get('stock_on_hand', 0.0)
            record.difference = res.get('difference', 0.0)
            record.description = res.get('description', False)

    sequence = fields.Integer(string='No')
    product_id = fields.Many2one('product.product', string='Product')
    
    uom_id = fields.Many2one('uom.uom', string='Satuan Barang', related='product_id.uom_id')
    product_code = fields.Char(string='Kode Barang', related='product_id.default_code')
    
    first_balance = fields.Float(string='Saldo Awal', compute=_compute_all)
    income = fields.Float(string='Jumlah Pemasukan Barang', compute=_compute_all)
    outcome= fields.Float(string='Jumlah Pengeluaran Barang', compute=_compute_all)
    adjustment = fields.Float(string='Adjustment', compute=_compute_all)
    last_balance = fields.Float(string='Saldo Akhir', compute=_compute_all)
    stock_opname = fields.Float(string='Stock Opname', compute=_compute_all)
    stock_enumeration = fields.Float(string='Hasil Pencacahan', compute=_compute_all)
    stock_on_hand = fields.Float(string='Jumlah Barang', compute=_compute_all)
    difference = fields.Float(string='Jumlah Selisih', compute=_compute_all)
    description = fields.Char(string='Description', compute=_compute_all)

    @api.model
    def _get_quantities(self, product_ids, date_from=None, date_to=None):
        start_date = datetime.strptime(date_from, "%Y-%m-%d")
        end_date = datetime.strptime(date_to, "%Y-%m-%d")
        res = product_ids._compute_quantities_dict_custom(from_date=date_from, to_date=date_to)
        res_awal = product_ids._compute_quantities_dict(False, False, False, to_date=start_date)
        res_akhir = product_ids._compute_quantities_dict(False, False, False, to_date=end_date)
        stock_inventory_line = self.env['stock.inventory.line']
        # sql = '''SELECT sinli.product_qty FROM stock_inventory_line sinli
        #     INNER JOIN stock_inventory sinv ON sinv.id = sinli.inventory_id
        #     WHERE DATE(sinv.date) >= DATE(%s) AND DATE(sinv.date) <= DATE(%s) AND sinv.state='done'
        #     '''
        # self._cr.execute(sql, (start_date, end_date))
        # stock_inventory_line = dict(self._cr.fetchall())
        result = dict()
        for product_id in product_ids:
            print(res[product_id.id])
            first_balance = res[product_id.id]['first_balance']
            stock_on_hand = res_awal[product_id.id]['qty_available']
            income = res_akhir[product_id.id]['incoming_qty']
            outcome = res_akhir[product_id.id]['outgoing_qty']
            last_balance = first_balance + income - outcome
            # last_balance = res_akhir[product_id.id]['first_balance']
            stock_opname = sum(stock_inventory_line.search([('product_id', '=', product_id.id), ('inventory_date', '>=', date_from), ('inventory_date', '<=', date_to)]).mapped('product_qty'))
            adjustment = stock_opname - first_balance - income
            stock_enumeration = first_balance + income - outcome
            # difference = abs(adjustment)
            difference = last_balance - stock_enumeration
            # if adjustment > 0.0:
            #     description = 'Positive Different'
            # elif adjustment < 0.0:
            #     description = 'Negative Different'
            # else:
            #     description = 'Matching'
            description = ''
            result[product_id.id] = {
                'first_balance': first_balance,
                'income': income,
                'outcome': outcome,
                'adjustment': adjustment,
                'last_balance': last_balance,
                'stock_opname': stock_opname,
                'stock_on_hand': stock_on_hand,
                'stock_enumeration': stock_enumeration,
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
            sw.is_it_inventory_warehouse = True AND pt.manuf_type = 'type_material'
        GROUP BY
            sm.product_id
        ORDER BY
            sm.product_id
        """

    @api.model
    def get_report_name(self):
        return _('Mutation of Raw Materials')

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'product_code', 'product_id', 'uom_id', 'stock_on_hand', 'first_balance', 'income',
            'outcome', 'adjustment', 'last_balance', 'stock_opname', 'difference', 'description'
        ]

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
