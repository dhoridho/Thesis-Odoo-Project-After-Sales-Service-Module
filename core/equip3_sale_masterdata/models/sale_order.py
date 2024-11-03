
from odoo import models, fields, api, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # def _get_init(self):
    #     IrConfigParam = self.env['ir.config_parameter'].sudo()
    #     return IrConfigParam.get_param('sale_order_multiple_pricelist', False)

    # @api.model
    # def get_values(self):
    #     res = super(SaleOrderLine, self).default_get(fields)
    #     IrConfigParam = self.env['ir.config_parameter'].sudo()
    #     res.update({
    #         'setting': IrConfigParam.get_param('sale_order_multiple_pricelist', False),
    #     })
    #     print("setting values :", IrConfigParam.get_param('sale_order_multiple_pricelist', False))
    #     return res

    setting = fields.Boolean(compute='_compute_setting', string='Setting')
    
    def _compute_setting(self):
        for rec in self:
            get_setting = self.env['ir.config_parameter'].sudo().get_param('sale_order_multiple_pricelist', False)
            rec.setting = get_setting

    def action_alternative_product(self):
        context = dict(self.env.context) or {}
        alternative = self.product_id.alternative_product_ids.ids
        alternative.extend(self.product_id.product_tmpl_id.alternative_product_ids.ids)
        context.update({
            'default_product_id': self.product_id.id,
            'default_alter_product_ids': [(6, 0, alternative)],
            'default_sale_line_id' : self.id,
        })
        return {
                'type': 'ir.actions.act_window',
                'name': 'Alternatives Products',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order.alternative.product',
                'target': 'new',
                'context' : context
            }

    def action_readonly(self):
        return True