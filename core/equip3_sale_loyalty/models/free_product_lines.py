from odoo import models,fields,api,_
from odoo.exceptions import ValidationError

class FreeProductLines(models.Model):
    _name = 'free.product.lines'
    _description = 'Free Product Lines'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1)
    uom_id = fields.Many2one('uom.uom', string='UOM', required=True)
    customer_target_id = fields.Many2one('customer.target', string='Customer Target')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = False
        self.description = False
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.description = self.product_id.display_name

class CustomerTarget(models.Model):
    _inherit = 'customer.target'

    free_product_line_ids = fields.One2many('free.product.lines', 'customer_target_id', string='Free Product')

    @api.constrains('free_product_line_ids')
    def _check_free_product_line_ids(self):
        data = []
        for record in self:
            for line in record.free_product_line_ids:
                if line.product_id.id in data:
                    raise ValidationError("You cannot add same Product Record Twice!")
                else:
                    data.append(line.product_id.id)
