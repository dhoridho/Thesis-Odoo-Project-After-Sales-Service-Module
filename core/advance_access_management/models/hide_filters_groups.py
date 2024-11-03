from odoo import fields,models,api,_
from lxml import etree

class hide_filters_groups(models.Model):
    _inherit = 'hide.filters.groups'

    restrict_custom_filter = fields.Boolean(help="The Add Custom Filter will be hidden in search view of selected model from the specified users.")
    restrict_custom_group = fields.Boolean(help="The Add Custom Broupby will be hidden in search view of selected model from the specified users.")