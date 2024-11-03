
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signature_privy_id = fields.Char(string="Privy Id")

    identity_number = fields.Char(string="Identity Number")
    signature_name = fields.Char(string="Full Name")
    date_of_birth = fields.Date(string="Date Of Birth")
    signature_mobile = fields.Char(string="Phone")
    signature_status = fields.Char(string="Status")
    signature_email = fields.Char(string="Email")
    selfie_img = fields.Binary(string="Selfie Image", attachment=True)
    selfie_img_name = fields.Char(string='Selfie Image Name', default='selfie.png')
    identity_image = fields.Binary(string="Identity Id", attachment=True)
    identity_image_name = fields.Char(string="Identity Image Name", default="identity.png")
    signature_country_id = fields.Many2one('res.country', string="Country")
    signature_reason = fields.Char(string="Reason")
    signature_token = fields.Char(string='Token')

    type = fields.Selection(selection_add=[('pic', 'PIC')])

    def get_default_field_value(self):
        config = self.env['ir.config_parameter']
        return config.sudo().get_param("customer_esignature")

    customer_esignature = fields.Boolean(string="Customer Signature", default=get_default_field_value,
                                         compute='_compute_customer_esignature')

    @api.constrains('type', 'child_ids')
    def _check_pic(self):
        for record in self:
            print("")
            # if record.child_ids and len(record.child_ids.filtered(lambda r: r.type == 'pic')) > 1:
            #     raise ValidationError('Customer can create only one PIC!')

    def _compute_customer_esignature(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.customer_esignature = IrConfigParam.get_param('customer_esignature')
