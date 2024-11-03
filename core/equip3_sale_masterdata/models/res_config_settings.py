from odoo import api , fields , models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_order_multiple_pricelist = fields.Boolean(string='Sale Order Multiple Pricelist', help="Show/hide apply button in sales/quotations and sale/order detail menu")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'sale_order_multiple_pricelist': IrConfigParam.get_param('sale_order_multiple_pricelist'),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('sale_order_multiple_pricelist', self.sale_order_multiple_pricelist)