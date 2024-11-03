# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # EIM Sandbox Configuration for Hashmicro - Facilitator
    gobiz_environment = fields.Selection([('sandbox','Sandbox (Testing)'), ('production','Production')], string='Environment', default='sandbox', config_parameter='base_setup.gobiz_environment')
    gobiz_sandbox_partner_id = fields.Char('Partner ID', config_parameter='base_setup.gobiz_sandbox_partner_id')
    gobiz_sandbox_client_id = fields.Char('Client ID', config_parameter='base_setup.gobiz_sandbox_client_id')
    gobiz_sandbox_client_secret = fields.Char('Client Secret', config_parameter='base_setup.gobiz_sandbox_client_secret')
    gobiz_sandbox_notification_secret_key = fields.Char('Notification Secret Key', config_parameter='base_setup.gobiz_sandbox_notification_secret_key')
    gobiz_sandbox_auth_base_url = fields.Char('Auth Base URL', default='https://integration-goauth.gojekapi.com', config_parameter='base_setup.gobiz_sandbox_auth_base_url')
    gobiz_sandbox_eim_base_url = fields.Char('EIM Base URL', default='https://api.sandbox.gobiz.co.id', config_parameter='base_setup.gobiz_sandbox_eim_base_url')

    #EIM Production Configuration for Hashmicro - Facilitator
    gobiz_production_partner_id = fields.Char('Partner ID', config_parameter='base_setup.gobiz_production_partner_id')
    gobiz_production_client_id = fields.Char('Client ID', config_parameter='base_setup.gobiz_production_client_id')
    gobiz_production_client_secret = fields.Char('Client Secret', config_parameter='base_setup.gobiz_production_client_secret')
    gobiz_production_notification_secret_key = fields.Char('Notification Secret Key', config_parameter='base_setup.gobiz_production_notification_secret_key')
    gobiz_production_auth_base_url = fields.Char('Auth Base URL', default='https://accounts.go-jek.com', config_parameter='base_setup.gobiz_production_auth_base_url')
    gobiz_production_eim_base_url = fields.Char('EIM Base URL', default='https://api.gobiz.co.id', config_parameter='base_setup.gobiz_production_eim_base_url')


    def action_open_online_outlet_gobiz_subscription(self):
        try:
            self.env['pos.online.outlet.gobiz.subscription'].action_sync()
        except Exception as e:
            pass
            
        action = self.env.ref('equip3_pos_online_gofood.pos_online_outlet_gobiz_subscription_action').read()[0]
        return action
