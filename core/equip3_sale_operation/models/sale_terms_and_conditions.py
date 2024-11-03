from odoo import api, fields, models, _

class SaleTermsAndConditions(models.Model):
    _name = 'sale.terms.and.conditions'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Sale Terms And Conditions"

    name = fields.Char(string="Name", required=True, tracking=True)
    description = fields.Text(string='Description', required=True, tracking=True)
    terms_and_conditions = fields.Html(string="Terms & Conditions", tracking=True)
