from odoo import api, fields, models


class DocumentType(models.Model):
    _name = 'it.inventory.document.type'
    _description = 'IT Inventory Document Type'
    _rec_name = 'document_code'

    document_code = fields.Char(string='Document Code', required=True)
    document_type = fields.Selection(string='Document Type', selection=[('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)
    description = fields.Char(string='Description')