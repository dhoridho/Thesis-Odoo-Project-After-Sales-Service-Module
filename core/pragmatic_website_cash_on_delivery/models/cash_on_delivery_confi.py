from odoo import api, fields, models,_
from odoo.exceptions import ValidationError,RedirectWarning,UserError
import re

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
   
  
    # cash_on_delivery_msg = fields.Many2one("cash.delivery",string='Message')
    cash_on_delivery = fields.Boolean(string='Cash On Delivery')
    min_cod_value = fields.Float(string="Minimum Cash on Delivery Value")
    max_cod_value = fields.Float(string="Maximum Cash on Delivery Value")
    cash_on_delivery_msg = fields.Text(string="Message")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        Param = self.env['ir.config_parameter'].sudo()
        res['cash_on_delivery'] = Param.sudo().get_param('pragmatic_website_cash_on_delivery.cash_on_delivery')
        res['min_cod_value'] = Param.sudo().get_param('pragmatic_website_cash_on_delivery.min_cod_value')
        res['max_cod_value'] = Param.sudo().get_param('pragmatic_website_cash_on_delivery.max_cod_value')
        res['cash_on_delivery_msg'] = Param.sudo().get_param('pragmatic_website_cash_on_delivery.cash_on_delivery_msg')
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'pragmatic_website_cash_on_delivery.cash_on_delivery', self.cash_on_delivery)
        self.env['ir.config_parameter'].sudo().set_param(
            'pragmatic_website_cash_on_delivery.min_cod_value',self.min_cod_value)
        self.env['ir.config_parameter'].sudo().set_param(
            'pragmatic_website_cash_on_delivery.max_cod_value', self.max_cod_value)
        self.env['ir.config_parameter'].sudo().set_param(
            'pragmatic_website_cash_on_delivery.cash_on_delivery_msg', self.cash_on_delivery_msg)
