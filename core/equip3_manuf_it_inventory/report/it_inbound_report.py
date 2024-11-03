import json
import calendar
from odoo import models, api, fields, tools, _


class ItInboundReport(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.inbound.report'
    _description = 'Inbound Report'
    _auto = False

    sequence = fields.Integer(string='No')
    document_type_id = fields.Many2one(comodel_name='it.inventory.document.type', string='Document Type')
    doc_type_id = fields.Many2one(comodel_name='ceisa.document.type', string='Jenis Dok.')
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
            cid.id AS id,
            ROW_NUMBER() OVER (ORDER BY cid.id) AS sequence,
            cid.document_type_id AS doc_type_id,
            cid.no_aju AS registration_number,
            cid.aju_date AS registration_date,
            picking.name AS request_number,
            picking.date_done AS date_done,
            picking.partner_id AS partner_id,
            cpl.product_id AS product_id,
            cpl.product_qty AS quantity,
            (cpl.product_qty * cpl.product_price) AS value,
            sw.id AS warehouse_id
        FROM
            ceisa_import_documents cid
        LEFT JOIN
            ceisa_products_line cpl
            ON (cpl.import_document_id = cid.id)
        LEFT JOIN
            stock_picking picking
            ON (picking.id = cid.picking_id)
        LEFT JOIN
            stock_location sl
            ON (sl.id = picking.location_dest_id)
        LEFT JOIN
            stock_warehouse sw
            ON (sw.id = sl.warehouse_id)
        ORDER BY
            cid.id
        """

    @api.model
    def get_report_name(self):
        return _('Laporan Pemasukan Barang')
        # return _('Inbound Report')

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'doc_type_id', 'registration_number', 'registration_date', 'request_number',
            'date_done', 'partner_id', 'product_code', 'product_id', 'uom_id', 'quantity', 'value'
        ]

    @api.model
    def get_default_action(self, xml_id):
        action = super(ItInboundReport, self).get_default_action(xml_id)
        document = self.env['ceisa.document.type'].sudo().search([
            ('code', '=', '20')
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
