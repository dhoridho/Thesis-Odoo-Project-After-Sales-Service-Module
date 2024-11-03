from odoo import models, api, fields, tools, _


class ItStockOpnameReport(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.stock.opname.report'
    _description = 'Stock Opname Report'
    _auto = False


    sequence = fields.Integer(string='No')
    date_done = fields.Datetime(string='Tanggal Pelaksanaan')
    product_id = fields.Many2one(comodel_name='product.product', string='Nama Barang')
    product_code = fields.Char(string='Kode Barang', related='product_id.default_code')
    product_type = fields.Selection(string='Kategori Barang', related='product_id.type')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Satuan Barang', related='product_id.uom_id')
    quantity = fields.Float(string='Jumlah Barang')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    description = fields.Char(string='Keterangan')

    def _query(self):
        return """
        SELECT
            sil.product_id AS id,
            ROW_NUMBER() OVER (PARTITION BY DATE(si.date) ORDER BY sil.product_id) AS sequence,
            DATE(si.date) as date_done,
            sil.product_id as product_id,
            sum(sil.product_qty) as quantity,
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
        return _('Laporan Stock Opname')

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'date_done', 'product_code', 'product_type', 'product_id', 'uom_id', 'quantity', 'description'
        ]

    @api.model
    def get_default_action(self, xml_id):
        action = super(ItStockOpnameReport, self).get_default_action(xml_id)
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
