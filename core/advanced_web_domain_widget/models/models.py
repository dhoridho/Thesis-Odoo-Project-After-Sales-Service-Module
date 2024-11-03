from odoo import api, fields, models, tools, _


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_widget_name(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        return self.sudo().search_read(domain, ['id', 'display_name'], offset, limit, order)
    
    @api.model
    def get_widget_count(self, args):
        return self.sudo().search_count(args)