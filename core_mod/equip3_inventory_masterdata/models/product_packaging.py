from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError, UserError

class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    packages_barcode_prefix = fields.Char(string="Packages Barcode Prefix")
    digits = fields.Integer(string="Digits", default=3)
    current_sequence = fields.Char(string="Current Sequence", default='1')
    product_id = fields.Many2many('product.product', string='Product', check_company=False)
    maximum_height = fields.Float(string="Maximum Height")
    maximum_length = fields.Float(string="Maximum Length")
    maximum_width = fields.Float(string="Maximum Width")
    maximum_volume = fields.Float(string="Maximum Volume", compute="_compute_maximum_volume")

    @api.onchange('digits')
    def _current_number_digits(self):
        number = self.current_sequence.lstrip('0')
        if self.digits < len(number):
            raise ValidationError(_('Digits Not Acceptable!'))
        current_sequence_length = len(self.current_sequence)
        if self.digits > current_sequence_length:
            number_length = len(number)
            original_number_length = self.digits - number_length
            add_zero_original_number = '0' * original_number_length
            self.current_sequence = add_zero_original_number + number
        else:
            self.current_sequence = self.current_sequence[-self.digits:]

    @api.depends('maximum_height', 'maximum_length', 'maximum_width')
    def _compute_maximum_volume(self):
        for record in self:
            record.maximum_volume = record.maximum_height * record.maximum_length * record.maximum_width
