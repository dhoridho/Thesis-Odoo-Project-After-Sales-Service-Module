# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    signature_to_confirm = fields.Boolean(string="Signature to Confirm", default=True)
    signature_signed_by = fields.Char(string="Signed By")
    signature_signed_on = fields.Date(string="Signed On")
    attachment_ids = fields.Many2many(comodel_name="ir.attachment",
                                      relation="rel_sale_esignature_ir_attachments",
                                      string="Attachments")

    def get_default_field_value(self):
        config = self.env['ir.config_parameter']
        return config.sudo().get_param("customer_esignature")

    customer_esignature = fields.Boolean(string="Customer Signature", default=get_default_field_value,
                                         compute='_compute_customer_esignature')

    def _compute_customer_esignature(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.customer_esignature = IrConfigParam.get_param('customer_esignature')

