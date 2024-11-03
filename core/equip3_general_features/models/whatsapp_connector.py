from odoo import _, api, fields, models
import re
from odoo.exceptions import ValidationError

class equip3WhatsAppConnector(models.Model):
    _name = 'whatsapp.connector'
    _description = 'Whatsapp Connector'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    name = fields.Char()
    app_id = fields.Char()
    channel_id = fields.Char()
    url = fields.Char()
    secret_key = fields.Char()
    is_use_chatroom = fields.Boolean(default=False)
    email = fields.Char()
    password = fields.Char()
    
    
    def write(self, vals):
        res =  super(equip3WhatsAppConnector,self).write(vals)
        
        if self.app_id:
            app_id = self.env['ir.config_parameter'].sudo().set_param('qiscus.api.appid',self.app_id)
        if self.url:
            domain = self.env['ir.config_parameter'].sudo().set_param('qiscus.api.url',self.url) 
        if self.channel_id:
            channel_id = self.env['ir.config_parameter'].sudo().set_param('qiscus.api.channel_id',self.channel_id) 
        if self.secret_key:
            token = self.env['ir.config_parameter'].sudo().set_param('qiscus.api.secret_key',self.secret_key) 
            
        self.env.cr.commit()
        
        syncron = self.env['qiscus.wa.template'].search([],limit=1)
        if syncron:
            syncron.ir_cron_syncronize_template()
        
        return res
    