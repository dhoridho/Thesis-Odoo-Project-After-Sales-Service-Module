from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    custom_uom_line = fields.One2many(comodel_name='custom.uom.line', inverse_name='product_id', string='Custom UoM Line')

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        for custom_uom_line in self.custom_uom_line:
            uom_ids = self.env['uom.uom'].search([('id', '=', custom_uom_line.uom_id.id)])
            if uom_ids:
                for uom_id in uom_ids:
                    product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.id)], limit=1)
                    ration_line = uom_id.product_ratio_line.filtered(lambda r: r.product_id.id == product_id.id)
                    if ration_line:
                        ration_line.ratio = custom_uom_line.ratio
                        ration_line.uom_ref_id = custom_uom_line.uom_ref_id.id
                        ration_line.description = custom_uom_line.description
                    else:
                        vals = {
                            'uom_id': custom_uom_line.uom_id.id,
                            'product_id': product_id.id,
                            'description': custom_uom_line.description,
                            'ratio': custom_uom_line.ratio,
                            'uom_ref_id': custom_uom_line.uom_ref_id.id,
                        }
                        self.env['product.ratio.line'].create(vals)
        return res


class CustomUomLine(models.Model):
    _name = 'custom.uom.line'
    _description = 'Custom Uom Line'

    product_id = fields.Many2one('product.template', string='Product')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM', required = True)
    description = fields.Char(string='Description')
    ratio = fields.Float(string='Ratio', required=True)
    uom_ref_id = fields.Many2one(comodel_name='uom.uom', string='Uom Reference Number', readonly = True)
    uom_id_domain = fields.Char(string='UoM Domain', compute='_compute_uom_id_domain')

    @api.constrains('uom_id')
    def _check_uom_id(self):
        for rec in self:
            exist_uom = self.env['custom.uom.line'].search([
                ('product_id', '=', rec.product_id.id),
                ('uom_id', '=', rec.uom_id.id),
                ('id', '!=', rec.id)
                ])
            if exist_uom:
                raise ValidationError(_('UoM already exists!'))

    @api.depends('product_id')
    def _compute_uom_id_domain(self):
        for rec in self:
            if rec.product_id:
                uom_ids = self.env['uom.uom'].search([('category_id', '=', rec.product_id.uom_id.category_id.id), ('is_custom_uom', '=', True)])
                rec.uom_id_domain = json.dumps([('id', 'in', uom_ids.ids)])

    

    @api.onchange('uom_id')
    def onchange_product_id(self):
        if self.uom_id:
            uom_obj = self.env['uom.uom'].search([('category_id', '=', self.uom_id.category_id.id)])
            self.description = f'1 {self.uom_id.name} {self.product_id.name} Equals to'
            self.uom_ref_id = sorted(uom_obj, key=lambda x: x.id)[0].id

    def unlink(self):
        if self._context and 'params' in self._context and self._context['params']['model'] == 'product.template':
            for custom_uom_line in self:
                uom_ids = self.env['uom.uom'].search([('id', '=', custom_uom_line.uom_id.id)])
                if uom_ids:
                    for uom_id in uom_ids:
                        product_id = self.env['product.product'].search([('product_tmpl_id', '=', custom_uom_line.product_id.id)], limit=1)
                        ration_line = uom_id.product_ratio_line.filtered(lambda r: r.product_id.id == product_id.id)
                        if ration_line:
                            ration_line.unlink()
        return super(CustomUomLine, self).unlink()