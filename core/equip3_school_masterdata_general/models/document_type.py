from odoo import fields, api, models, _


class DocumentType(models.Model):
    _name = "document.type"
    _description = "Document Type"

    name = fields.Char(string="Name", required=True)
    seq_no = fields.Char(
        string="Sequence",
        readonly=True,
        default=lambda self: _("New"),
        help="Sequence of the document",
    )
    doc_type = fields.Char(string="Document Type", required=True, help="Document type")
