from odoo import api, fields, models, _



class surveyCategory(models.Model):
    _name = "survey.category"
    _description = "Survey Category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char()