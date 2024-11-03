from odoo import fields,models,api



class OtpEmail(models.Model):
    _name = 'otp.email'
    
    opt_code = fields.Char()
    email = fields.Char()
    expire = fields.Datetime()
    is_use =  fields.Boolean()
    is_use_reset =  fields.Boolean()
    token = fields.Char()
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)
    
class OtpPhone(models.Model):
    _name = 'otp.phone'
    
    opt_code = fields.Char()
    phone = fields.Char()
    expire = fields.Datetime()
    is_use =  fields.Boolean()
    is_use_reset =  fields.Boolean()
    token = fields.Char()
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)