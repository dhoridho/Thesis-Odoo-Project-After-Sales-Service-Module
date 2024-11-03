# -*- coding: utf-8 -*-

import json

from odoo import fields, models, _

class PosConfig(models.Model):
    _inherit = "pos.config"

    is_difference_value_opening_control_validation = fields.Boolean('Difference Value Opening Control Validation')
    is_cash_management_with_validation = fields.Boolean('Cash Management With Validation')
    cashbox_payment_method_id = fields.Many2one('pos.payment.method', string='Cashbox Payment Method')
    pos_cashbox_product_services = fields.Text(string='POS Cashbox Product Services', compute='_compute_pos_cashbox_product_services')
    cashbox_line_amount = fields.Float(string='Cashbox Lines Amount', compute='_compute_cashbox_line_amount')

    def _compute_cashbox_line_amount(self):
        for rec in self:
            rec.cashbox_line_amount = sum([l.subtotal for l in rec.pos_cashbox_lines_ids])

    def _compute_pos_cashbox_product_services(self):
        # TODO: Get 100 product for cash management
        for rec in self:
            domain = [('product_tmpl_id.is_for_cash_management','=', True)]
            products = self.env['product.product'].search_read(domain, ['id', 'product_tmpl_id', 'name'], limit=100)
            rec.pos_cashbox_product_services = json.dumps(products)


    def action_show_cashbox_history(self):
        return {
            'name': _('Cashbox History'),
            'res_model': 'pos.cashbox.history',
            'view_mode': 'tree',
            'views': [
                (self.env.ref('equip3_pos_cashbox.pos_cashbox_history_tree').id, 'tree'),
            ],
            'type': 'ir.actions.act_window',
            'domain': ['|',('pos_config_id', '=', self.id), ('pos_session_id.config_id','=', self.id)],
        }
