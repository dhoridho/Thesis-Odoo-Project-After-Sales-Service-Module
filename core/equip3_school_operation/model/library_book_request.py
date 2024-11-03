from odoo import _, api, fields, models

class LibraryBookRequest(models.Model):
    _inherit = "library.book.request"
    _order = "create_date desc"

    @api.model
    def create(self, vals):
        res = super(LibraryBookRequest, self).create(vals)
        seq_obj = self.env["ir.sequence"]
        res.write(
            {"req_id": (seq_obj.next_by_code("book.request") or "New")}
        )
        return res
