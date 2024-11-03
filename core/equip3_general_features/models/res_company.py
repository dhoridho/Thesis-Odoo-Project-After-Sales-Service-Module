
from odoo import models, fields, api, _


class ResCompany(models.Model):
    _name = 'res.company'
    _inherit = ['res.company', 'mail.thread', 'mail.activity.mixin']

    partner_id = fields.Many2one(tracking=True)
    street = fields.Char(tracking=True)
    phone = fields.Char(tracking=True)
    email = fields.Char(tracking=True)
    vat = fields.Char(tracking=True)
    company_registry = fields.Char(tracking=True)
    currency_id = fields.Many2one(tracking=True)
    parent_id = fields.Many2one(tracking=True)
    social_twitter = fields.Char(tracking=True)
    social_facebook = fields.Char(tracking=True)
    social_github = fields.Char(tracking=True)
    social_linkedin = fields.Char(tracking=True)
    social_youtube = fields.Char(tracking=True)    
    social_instagram = fields.Char(tracking=True)
    city_id = fields.Many2one('res.country.city')
    active = fields.Boolean('Active', default=True)
    tax_cutter_name = fields.Many2one('res.users', string='Tax Cutter Name')
    tax_cutter_npwp = fields.Char('Tax Cutter NPWP')
    
    
    @api.onchange('state_id')
    def _onchange_state_id(self):
        for record in self:
            if record.state_id:
                if record.city_id:
                    if record.city_id.state_id.id != record.state_id.id:
                        record.city_id = False
                return { 'domain': {'city_id': [('state_id', '=',record.state_id.id)]}}
       

    
    @api.onchange('city_id')
    def _onchange_city(self):
        for record in self:
            if record.city_id:
                record.city =  record.city_id.name
                record.state_id = record.city_id.state_id.id
                record.country_id = record.state_id.country_id.id
                # return { 'domain': {'city_id': [('state_id', '=',record.state_id.id)]}}
            else:
                record.city = ''
    


