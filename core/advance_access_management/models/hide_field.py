from odoo import fields, models, api, _
from lxml import etree

class hide_field(models.Model):
    _inherit = 'hide.field'

    create_option = fields.Boolean('Remove Create Option')
    edit_option = fields.Boolean('Remove Edit Option')
    
