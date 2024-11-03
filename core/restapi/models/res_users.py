from odoo import models,fields

class resUsers(models.Model):
    _inherit = 'res.users'
    
    firebase_token =  fields.Char(default="[]")
    
    
    def action_generate_authentication(self):
        for rec in self:
            auth =  self.env['auth.auth'].search([('user_id','=',rec.id)])
            if not auth:
                new_auth = self.env['auth.auth'].create({'user_id':rec.id,'name':f"{rec.name} Auth"})
