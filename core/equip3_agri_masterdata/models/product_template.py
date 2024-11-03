from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_agriculture_product = fields.Boolean(string='Is an Agriculture Product', default=False)
    agri_product_type = fields.Selection(selection=[('crop', 'Crop'), ('fruit', 'Fruit')], string='Agriculture Product Type')

    @api.onchange('is_agriculture_product')
    def _onchange_is_agriculture_product(self):
        if not self.is_agriculture_product:
            self.agri_product_type = False

    @api.constrains('agri_product_type')
    def _check_agri_product_type(self):
        for record in self:
            if record.agri_product_type == 'crop' and record.tracking not in ('lot', 'serial'):
                raise ValidationError(_('Please select Tracking to Lot or Serial Number'))
