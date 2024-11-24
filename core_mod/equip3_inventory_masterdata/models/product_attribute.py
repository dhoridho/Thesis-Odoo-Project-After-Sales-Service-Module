from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_short_name = fields.Boolean(compute='compute_short_name')
    product_brand_ids = fields.Many2many('product.brand', string="Brand")

    @api.model
    def create(self, vals):
        if vals['name']:
            attribute_ids = self.env['product.attribute'].search(
                [('name', '=', vals['name'])], limit=1)
            if attribute_ids:
                raise ValidationError(_('product.attribute: %s is already exists!' % vals['name']))
        return super(StockProductAttribute, self).create(vals)

    def compute_short_name(self):
        for sh in self.value_ids:
            s = ''.join(sh. name.split())
            sh.short_name = (s[:2]).upper()
        self.is_short_name = True

    # @api.onchange('value_ids')
    # def get_short_name(self):
    #     for record in self:
    #         if len(record.short_name) >= 2:
    #             record.short_name = (record.name[:2]).upper()

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    short_name = fields.Char('Short Name', required=True, size=3)

    @api.onchange('name')
    def get_short_name(self):
        for record in self:
            if record.name != False:
                s = ''.join(record.name.split())
                # s.replace(" ", "")
                record.short_name = (s[:2]).upper()

    @api.model
    def create(self, vals):
        if 'short_name' not in vals:
            name = vals['name'].split(" ")
            res_short_name = name[0][0:2] if len(
                name) == 1 else name[0][0] + name[1][0]
            vals['short_name'] = res_short_name.upper()
        res = super().create(vals)
        return res
