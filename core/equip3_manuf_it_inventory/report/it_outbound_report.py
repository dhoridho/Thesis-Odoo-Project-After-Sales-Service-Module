import json
import calendar
from odoo import models, api, fields, tools, _


class ItOutboundReport(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.outbound.report'
    _description = 'Outbound Report'
    _auto = False

    sequence = fields.Integer(string='No')
    document_type_id = fields.Many2one(comodel_name='it.inventory.document.type', string='Document Type')
    doc_type_id = fields.Many2one(comodel_name='ceisa.document.type', string='Jenis Dok')
    registration_number = fields.Char(string='No. Daftar')
    registration_date = fields.Datetime(string='Tgl. Daftar')
    request_number = fields.Char(string='No. Dok.')
    note = fields.Char(string='Notes')
    date_done = fields.Datetime(string='Tanggal')
    group_id = fields.Many2one(comodel_name='procurement.group', string='Purchase Order')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Nama Pengirim')
    product_id = fields.Many2one(comodel_name='product.product', string='Nama Barang')
    product_code = fields.Char(string='Kode Barang', related="product_id.default_code")
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Satuan', related='product_id.uom_id')
    quantity = fields.Float(string='Jumlah')
    value = fields.Float(string='Total')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')

    def _query(self):
        return """
        SELECT
            ced.id AS id,
            ROW_NUMBER() OVER (ORDER BY ced.id) AS sequence,
            ced.document_type_id AS doc_type_id,
            ced.no_aju AS registration_number,
            ced.aju_date AS registration_date,
            picking.name AS request_number,
            picking.date_done AS date_done,
            picking.partner_id AS partner_id,
            cpl.product_id AS product_id,
            cpl.product_qty AS quantity,
            (cpl.product_qty * cpl.product_price) AS value,
            sw.id AS warehouse_id
        FROM
            ceisa_export_documents ced
        LEFT JOIN
            ceisa_products_line cpl
            ON (cpl.export_document_id = ced.id)
        LEFT JOIN
            stock_picking picking
            ON (picking.id = ced.picking_id)
        LEFT JOIN
            stock_location sl
            ON (sl.id = picking.location_dest_id)
        LEFT JOIN
            stock_warehouse sw
            ON (sw.id = sl.warehouse_id)
        ORDER BY
            ced.id
        """

    @api.model
    def get_report_name(self):
        return _('Laporan Pengeluaran Barang')
        # return _('Outbound Report')

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'doc_type_id', 'registration_number', 'registration_date', 'request_number',
            'date_done', 'partner_id', 'product_code', 'product_id', 'uom_id', 'quantity', 'value'
        ]

    @api.model
    def get_default_action(self, xml_id):
        action = super(ItOutboundReport, self).get_default_action(xml_id)
        document = self.env['ceisa.document.type'].sudo().search([
            ('code', '=', '30')
        ], limit=1).id
        context = eval(action.get('context', '').strip() or '{}', self.env.context)
        context['document'] = document

        domain = eval(action.get('domain') or '[]', self.env.context)
        domain += [
            ('warehouse_id', '=', context.get('warehouse', False)),
            ('doc_type_id', '=', document),
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
