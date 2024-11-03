from odoo import models, fields, api, _
import qrcode
import base64
from io import BytesIO

class ProductWarrantyInherit(models.Model):
    _inherit = 'product.warranty'

    qr_code = fields.Binary("QR Code", attachment=True)
    picking_id = fields.Many2one('stock.picking', string="Picking")
    remaining_warranty_days = fields.Char(string='Remaining Warranty Days', compute='_compute_remaining_warranty_days')

    @api.depends('warranty_end_date')
    def _compute_remaining_warranty_days(self):
        for rec in self:
            if rec.warranty_end_date:
                remaining_day = rec.warranty_end_date - fields.Date.context_today(self)
                if remaining_day.days < 0:
                    rec.remaining_warranty_days = 0
                else:
                    rec.remaining_warranty_days = f'{remaining_day.days} days'
            else:
                rec.remaining_warranty_days = False

    def state_update(self):
        res = super(ProductWarrantyInherit, self).state_update()
        base_url = self.env['ir.config_parameter'].get_param(
            'web.base.url')
        base_url += '/page/warranty_information/?product=%s/?serial=%s'%(self.id, self.product_serial_id.name)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(base_url)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        self.qr_code = qr_image
        return res
