# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    use_sale_order_note = fields.Boolean(
        string='Default Terms & Conditions')
    sale_order_note = fields.Text(
        string='Default Terms and Conditions', translate=True)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    use_sale_order_note = fields.Boolean(
        related='company_id.use_sale_order_note', readonly=False,
        string='Default Terms & Conditions')
    sale_order_note = fields.Text(
        related='company_id.sale_order_note', readonly=False,
        string="Terms & Conditions")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _default_note(self):
        return self.env.company.sale_order_note or ''

    note = fields.Text('Terms and conditions', default=_default_note)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        """
        if not self.partner_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.partner_id.address_get(['delivery', 'invoice'])
        partner_user = self.partner_id.user_id or self.partner_id.commercial_partner_id.user_id
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'user_id': partner_user.id or self.env.uid
        }
        if self.env['ir.config_parameter'].sudo().get_param('sale_order_terms_knk.use_sale_order_note') and self.env.company.sale_order_note:
            values['note'] = self.with_context(lang=self.partner_id.lang).env.company.sale_order_note

        # Use team of salesman if any otherwise leave as-is
        values['team_id'] = partner_user.team_id.id if partner_user and partner_user.team_id else self.team_id
        self.update(values)