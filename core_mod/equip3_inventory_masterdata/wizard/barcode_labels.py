from odoo import fields, models, api


class BarcodeProductLines(models.TransientModel):
    _inherit = "barcode.product.lines"

    barcode = fields.Many2one("product.template.barcode",
                              string="Barcode",
                              domain="[('product_id', '=', product_id)]",
                              default=lambda self:self.product_id.barcode_line_ids and self.product_id.barcode_line_ids[0])

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for rec in self:
            if self.product_id.multi_barcode:
                rec.barcode = self.product_id.barcode_line_ids and self.product_id.barcode_line_ids[0]