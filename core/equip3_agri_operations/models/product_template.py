from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_agriculture_product = fields.Boolean(string='Is an Agriculture Product', default=False)
    agri_crop_type = fields.Selection(selection=[('palm', 'Palm'), ('cane', 'Sugar Cane')], string='Crop Type')
    agri_product_type = fields.Selection(selection=[('crop', 'Crop'), ('fruit', 'Fruit')], string='Agriculture Product Type')

    @api.onchange('is_agriculture_product')
    def _onchange_is_agriculture_product(self):
        if not self.is_agriculture_product:
            self.agri_crop_type = False
            self.agri_product_type = False
