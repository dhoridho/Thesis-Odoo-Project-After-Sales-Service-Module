# -*- coding: utf-8 -*-

from odoo import api, models, fields, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    allow_create_member_in_pos_screen = fields.Boolean(string='Allow Create Member in POS Screen', default=False, config_parameter='base_setup.allow_create_member_in_pos_screen')
    pkp_customer = fields.Many2one("res.partner",string="PKP Customer")

    membership_pluspoint_rounding = fields.Boolean(string="Plus Point Rounding", 
        related="company_id.membership_pluspoint_rounding", readonly=False)
    membership_pluspoint_rounding_type = fields.Selection(string="Membership PlusPoint Rounding",
        related="company_id.membership_pluspoint_rounding_type", readonly=False)
    membership_pluspoint_rounding_multiplier = fields.Selection(string="Membership PlusPoint Rounding Multiplier",
        related="company_id.membership_pluspoint_rounding_multiplier", readonly=False)
    is_pos_use_deposit = fields.Boolean('Deposit', related='company_id.is_pos_use_deposit', readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        partner_id= int(self.env['ir.config_parameter'].sudo().get_param('pkp_customer_id'))
        res['pkp_customer'] = partner_id
        return res

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.pkp_customer:
            self.env['ir.config_parameter'].sudo().set_param('pkp_customer_id', int(self.pkp_customer.id))
