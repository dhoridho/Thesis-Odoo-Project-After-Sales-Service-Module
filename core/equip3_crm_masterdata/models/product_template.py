
from odoo import models, fields, api, _
from odoo.http import request


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    url_pic = fields.Char("URL", compute='compute_url_pic', store=True)

    @api.depends('image_1920')
    def compute_url_pic(self):
        for res in self:
            if res.image_1920:
                res.url_pic = self.env['ir.config_parameter'].sudo().get_param('web.base.url')+ '/web/image/product.template/' + str(res.id) + '/image_1920'
            else:
                res.url_pic = False