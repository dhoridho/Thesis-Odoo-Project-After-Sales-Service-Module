# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    buffer_date = fields.Integer(string="Default Buffer Date", help="Change maximum days you can change menu")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'buffer_date': IrConfigParam.get_param('buffer_date', 1),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('buffer_date', self.buffer_date)

    @api.constrains('buffer_date')
    def check_is_negative_number(self):
        if self.buffer_date < 0:
            raise ValidationError('Buffer date can only be positive number')