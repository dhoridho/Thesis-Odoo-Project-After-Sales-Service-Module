from odoo import _, api, fields, models


class SchoolDocumentType(models.Model):
    _inherit = "document.type"

    name = fields.Char(string="Name", required=True)
    doc_type = fields.Char("Document Type", required=False, help="Document type")
    seq_no = fields.Char(
        "Sequence",
        readonly=True,
        default=lambda self: _("New"),
        help="Sequence of the document",
    )
    active = fields.Boolean(
        default=True, help="Activate/Deactivate Document Type"
    )

    @api.model
    def create(self, vals):
        if vals.get("seq_no", _("New")) == _("New"):
            vals["seq_no"] = self.env["ir.sequence"].next_by_code("document.type") or _(
                "New"
            )
        return super(SchoolDocumentType, self).create(vals)
