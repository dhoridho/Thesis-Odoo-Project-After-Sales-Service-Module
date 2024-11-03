from odoo import api, fields, models
from odoo.exceptions import Warning


class Equip3RentalProductTemplate(models.Model):
    _inherit = "product.template"

    type = fields.Selection(
        string="Product Type",
        compute="compute_type",
        store=True,
        readonly=False
        
    )
    type1 = fields.Selection([
        ('asset', 'Asset'),
        ('product', 'Storable Product')
    ],
    string='Product Type',
    default='product',  
    required=True,
    help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
    'A consumable product is a product for which stock is not managed.\n'
    'A service is a non-material product you provide.')


    @api.onchange('type1')
    def _compute_type(self):
        for line in self:
            line.type = line.type1

