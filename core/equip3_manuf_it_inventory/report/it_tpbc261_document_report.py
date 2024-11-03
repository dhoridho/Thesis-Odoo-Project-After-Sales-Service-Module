import json
import calendar
from odoo import models, api, fields, tools, _


class ItTPBC261DocumentReport(models.Model):
    _inherit = 'it.inventory.list.report'
    _name = 'it.tpbc261.document.report'
    _description = 'Document TPB BC-2.6.1 Report'
    _auto = False

    sequence = fields.Integer(string='No')
    document_type_id = fields.Many2one(comodel_name='it.inventory.document.type', string='Document Type')
    doc_type_id = fields.Many2one(comodel_name='ceisa.document.type', string='Ceisa Document Type')
    registration_number = fields.Char(string='Registration Number')
    registration_date = fields.Datetime(string='Registration Date')
    request_number = fields.Char(string='Request Number')
    note = fields.Char(string='Notes')
    date_done = fields.Datetime(string='Receiving Date')
    group_id = fields.Many2one(comodel_name='procurement.group', string='Purchase Order')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Vendor')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    product_code = fields.Char(string='Product Code', related="product_id.default_code")
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM', related='product_id.uom_id')
    quantity = fields.Float(string='Qty')
    value = fields.Float(string='Total')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')

    def _query(self):
        return """
        SELECT
            tpb.id AS id,
            ROW_NUMBER() OVER (ORDER BY tpb.id) AS sequence,
            tpb.document_type_id AS doc_type_id,
            tpb.no_aju AS registration_number,
            tpb.aju_date AS registration_date,
            intrans.name AS request_number,
            intrans.arrival_date AS date_done,
            tpb.owner_partner_id AS partner_id,
            cpl.product_id AS product_id,
            cpl.product_qty AS quantity,
            (cpl.product_qty * cpl.product_price) AS value
        FROM
            ceisa_documents_bc261 tpb
        LEFT JOIN
            ceisa_products_line cpl
            ON (cpl.import_document_id = tpb.id)
        LEFT JOIN
            internal_transfer intrans
            ON (intrans.id = tpb.internal_transfer_id)
        ORDER BY
            tpb.id
        """

    @api.model
    def get_report_name(self):
        return _('Document TPB BC-261 Report')

    # @api.model
    # def _get_header_fields(self):
    #     return [
    #         'sequence', 'doc_type_id', 'registration_number', 'registration_date', 'request_number', 'note',
    #         'date_done', 'group_id', 'partner_id', 'product_code', 'product_id', 'uom_id', 'quantity', 'value'
    #     ]

    @api.model
    def _get_header_fields(self):
        return [
            'sequence', 'doc_type_id', 'registration_number', 'registration_date', 'request_number',
            'date_done', 'partner_id', 'product_code', 'product_id', 'uom_id', 'quantity', 'value'
        ]

    @api.model
    def get_default_action(self, xml_id):
        action = super(ItTPBC261DocumentReport, self).get_default_action(xml_id)
        # document = self.env['it.inventory.document.type'].sudo().search([
        #     ('document_type', '=', 'inbound')
        # ], limit=1).id
        document = self.env['ceisa.document.type'].sudo().search([
            ('code', 'in', ['20', '23', '262', '40'])
        ], limit=1).id
        context = eval(action.get('context', '').strip() or '{}', self.env.context)
        context['document'] = document

        domain = eval(action.get('domain') or '[]', self.env.context)
        # domain += [
        #     # ('warehouse_id', '=', context.get('warehouse', False)),
        #     # ('doc_type_id', '=', document),
        # ]

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
