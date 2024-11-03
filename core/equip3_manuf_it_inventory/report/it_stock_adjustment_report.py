from odoo import models, api, fields, tools, _
from datetime import datetime
from dateutil.relativedelta import relativedelta



class ItStockAdjustmentReport(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.stock.adjustment.report'
    _description = 'Stock Adjustment Report'
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
            last_balance = res.get('last_balance', 0.0)
            enumeration = record.stock_enumeration or 0.0
            record.first_balance = res.get('first_balance', 0.0)
            record.income = res.get('income', 0.0)
            record.outcome = res.get('outcome', 0.0)
            record.stock_on_hand = res.get('stock_on_hand', 0.0)
            record.adjustment = res.get('adjustment', 0.0)
            record.last_balance = last_balance
            record.difference = last_balance - enumeration

    sequence = fields.Integer(string='No')
    date_done = fields.Datetime(string='Tanggal Pelaksanaan')
    product_id = fields.Many2one(comodel_name='product.product', string='Nama Barang')
    product_code = fields.Char(string='Kode Barang', related='product_id.default_code')
    product_type = fields.Selection(string='Kategori Barang', related='product_id.type')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Satuan', related='product_id.uom_id')
    quantity = fields.Float(string='Jumlah Barang')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    first_balance = fields.Float(string='Saldo Awal', compute=_compute_all)
    income = fields.Float(string='Jumlah Pemasukan Barang', compute=_compute_all)
    outcome= fields.Float(string='Jumlah Pengeluaran Barang', compute=_compute_all)
    adjustment = fields.Float(string='Penyesuaian (Adjustment)', compute=_compute_all)
    last_balance = fields.Float(string='Saldo Akhir', compute=_compute_all)
    # stock_opname = fields.Float(string='Stock Opname', compute=_compute_all)
    stock_enumeration = fields.Float(string='Hasil Pencacahan')
    stock_on_hand = fields.Float(string='Jumlah Barang Tersedia', compute=_compute_all)
    difference = fields.Float(string='Jumlah Selisih', compute=_compute_all)
    description = fields.Char(string='Keterangan')

    @api.model
    def _get_quantities(self, product_ids, date_from=None, date_to=None):
        start_date = fields.Datetime.now().replace(day=1)
        if not date_from:
            date_from = start_date
        if not date_to:
            date_to = fields.Datetime.now()

        ### From Stock Card ###
        stock_data = self.get_product_stock_movements(product_ids, date_from, date_to)
        warehouse_wise_stock_data = self.prepare_data_to_write(stock_data=stock_data)
        if not warehouse_wise_stock_data:
            return False

        warehouse_wise_stock_data = self._add_usage_scrap(warehouse_wise_stock_data, date_from, date_to)
        warehouse_wise_stock_data = self._add_valuations(warehouse_wise_stock_data, date_from, date_to)
        result = dict()
        for warehouse, stock_data_value in warehouse_wise_stock_data.items():
            warehouse_id, warehouse_name = warehouse
            if not warehouse_id:
                continue
            first_balance = stock_data_value.get('opening_stock', 0.0)
            stock_on_hand = stock_data_value.get('value', 0.0)
            income = stock_data_value.get('internal_in', 0.0)
            outcome = stock_data_value.get('internal_out', 0.0)
            last_balance = stock_data_value.get('closing', 0.0)
            adjust_in = stock_data_value.get('adjustment_in', 0.0)
            adjust_out = stock_data_value.get('adjustment_out', 0.0)
            adjustment = adjust_in + adjust_out
            result[stock_data_value.get('product_id')] = {
                'first_balance': first_balance,
                'income': income,
                'outcome': outcome,
                'adjustment': adjustment,
                'last_balance': last_balance,
                'stock_on_hand': stock_on_hand,
            }
        return result

    def get_product_stock_movements(self, product_ids, start_date, end_date):
        category_ids = {}
        company_ids = {}
        warehouse = self.env.context.get('warehouse', False)
        warehouse_id = self.env['stock.warehouse'].browse(warehouse)
        warehouses = warehouse_id and set(warehouse_id.ids) or {}
        products = product_ids and set(product_ids.ids) or {}
        query = """
            Select * from get_products_stock_movements('%s','%s','%s','%s','%s','%s')
        """%(company_ids, products, category_ids, warehouses, start_date, end_date)
        # print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data

    def prepare_data_to_write(self, stock_data={}):
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def _add_usage_scrap(self, warehouse_wise_stock_data, start_date=None, end_date=None):

        day_before = datetime.strptime(start_date, '%Y-%m-%d') - relativedelta(days=1)
        day_after = datetime.strptime(end_date, '%Y-%m-%d') + relativedelta(days=1)

        def _where_clause(product_ids):
            product_ids_str = ','.join([str(pid) for pid in product_ids if pid])
            return ' AND '.join([
                "ss.product_id in (%s)" % product_ids_str,
                "ss.date_done > '%s'" % day_before,
                "ss.date_done < '%s'" % day_after,
                "ut.usage_type in ('usage', 'scrap')",
                "ssr.state = 'validated'"
            ])

        def _stock_scrap(warehouse_data):
            product_ids = [o['product_id'] for o in warehouse_data.values()]
            self._cr.execute('''SELECT
                ut.usage_type, ss.product_id, sum(ss.scrap_qty) as scrap_qty
            FROM
                stock_scrap ss
            LEFT JOIN
                stock_scrap_request ssr ON (ssr.id = ss.scrap_id)
            LEFT JOIN
                usage_type ut ON (ut.id = ssr.scrap_type)
            WHERE
                %s
            GROUP BY
                ut.usage_type, ss.product_id''' % _where_clause(product_ids))

            records = self._cr.dictfetchall()
            usages = {o['product_id']: o['scrap_qty'] for o in records if o['usage_type'] == 'usage'}
            scraps = {o['product_id']: o['scrap_qty'] for o in records if o['usage_type'] == 'scrap'}
            return usages, scraps

        for (warehouse_id, warehouse_name), stock_data in warehouse_wise_stock_data.items():
            if not warehouse_id:
                continue

            usage_data, scrap_data = _stock_scrap(stock_data)

            for key, data in stock_data.items():
                product_id = self.env['product.product'].browse(data['product_id'])
                usage_qty = usage_data.get(product_id.id, 0.0)
                scrap_qty = scrap_data.get(product_id.id, 0.0)

                # ????????
                if data.get('adjustment_out', 0.0) == 0.0:
                    adjustment_out = data.get('adjustment_out', 0.0)
                else:
                    adjustment_out = data.get('adjustment_out', 0.0)
                    if usage_qty > 0:
                        adjustment_out -= usage_qty
                    if scrap_qty > 0:
                        adjustment_out -= scrap_qty

                data.update({
                    'product_uom': product_id.uom_id.name,
                    'product_name': product_id.display_name,
                    'product_usage_quantity': usage_qty,
                    'product_scrap_quantity': scrap_qty,
                    'adjustment_out': adjustment_out
                })
        return warehouse_wise_stock_data

    def _add_valuations(self, warehouse_wise_stock_data, start_date=None, end_date=None):
        tommorow_of_end = datetime.strptime(end_date, '%Y-%m-%d') + relativedelta(days=1)
        warehouse_ids = [o[0] for o in warehouse_wise_stock_data.keys()]
        warehouse_ids_str = ','.join([str(wid) for wid in warehouse_ids if wid])
        def _svl_until(to_date, operator='<'):
            self._cr.execute('''SELECT
                warehouse_id, product_id, sum(value) as value
            FROM
                stock_valuation_layer
            WHERE
                date %s '%s' AND warehouse_id in (%s)
            GROUP BY
                warehouse_id, product_id''' % (operator, to_date, warehouse_ids_str))

            valuations = {}
            for o in self._cr.dictfetchall():
                if o['warehouse_id'] not in valuations:
                    valuations[o['warehouse_id']] = {o['product_id']: o['value']}
                else:
                    valuations[o['warehouse_id']][o['product_id']] = o['value']
            return valuations

        # start_date excluded
        opening_valuations = _svl_until(start_date)
        closing_valuations = _svl_until(tommorow_of_end)
        current_valuations = _svl_until(fields.Datetime.now(), operator='<=')

        for (warehouse_id, warehouse_name), stock_data in warehouse_wise_stock_data.items():
            if not warehouse_id:
                continue
            for key, data in stock_data.items():
                opening_value = opening_valuations.get(warehouse_id, {}).get(data['product_id'], 0.0)
                closing_value = closing_valuations.get(warehouse_id, {}).get(data['product_id'], 0.0)
                current_value = current_valuations.get(warehouse_id, {}).get(data['product_id'], 0.0)
                data.update({
                    'value': current_value,
                    'opening_value': opening_value,
                    'closing_value': closing_value,
                })
        return warehouse_wise_stock_data

    def _query(self):
        return """
        SELECT
            sil.product_id AS id,
            ROW_NUMBER() OVER (ORDER BY sil.product_id) AS sequence,
            DATE(si.date) as date_done,
            sil.product_id as product_id,
            sum(sil.product_qty) as quantity,
            sum(sil.product_qty) as stock_enumeration,
            si.warehouse_id AS warehouse_id,
            '' as description
        FROM
            stock_inventory_line sil
		LEFT JOIN 
			stock_inventory si
			ON (sil.inventory_id = si.id)
        LEFT JOIN
            product_product pp
            ON (pp.id = sil.product_id)
        LEFT JOIN
            product_template pt
            ON (pt.id = pp.product_tmpl_id)
        LEFT JOIN
            stock_warehouse sw
            ON (sw.id = si.warehouse_id)
        GROUP BY
            date_done, warehouse_id, product_id
        ORDER BY
            date_done, product_id
        """

    @api.model
    def get_report_name(self):
        return _('Laporan Data Adjustment')

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'date_done', 'product_code', 'product_id', 'product_type', 'quantity', 'uom_id',
            'stock_on_hand', 'first_balance', 'income', 'outcome', 'adjustment', 'last_balance',
            'stock_enumeration', 'difference', 'description'
        ]

    @api.model
    def get_default_action(self, xml_id):
        action = super(ItStockAdjustmentReport, self).get_default_action(xml_id)
        context = eval(action.get('context', '').strip() or '{}', self.env.context)

        domain = eval(action.get('domain') or '[]', self.env.context)
        domain += [
            ('warehouse_id', '=', context.get('warehouse', False)),
        ]

        if context.get('date_from', False):
            domain += [('date_done', '>=', context['date_from'])]
        if context.get('date_to', False):
            domain += [('date_done', '<=', context['date_to'])]

        action['context'] = context
        action['domain'] = domain
        return action

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
