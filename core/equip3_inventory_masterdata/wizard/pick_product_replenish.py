from odoo import models, fields, api, _


class PickProductReplenish(models.TransientModel):
    _name = 'pick.product.replenish'
    _description = 'Pick Product Replenish'

    @api.model
    def default_get(self, allfields):
        res = super(PickProductReplenish, self).default_get(allfields)
        if self.env.context.get('domain_product_ids', False):
            res['product_id'] = self.env.context.get('domain_product_ids')[0]
        if self.env.context.get('domain_product_tmpl_ids', False):
            res['product_tmpl_id'] = self.env.context.get('domain_product_tmpl_ids')[0]
        return res

    @api.model
    def _domain_product(self):
        if not self.env.context.get('domain_product_ids', False):
            return []
        return [('id', 'in', self.env.context.get('domain_product_ids', []))]

    @api.model
    def _domain_product_tmpl(self):
        if not self.env.context.get('domain_product_tmpl_ids', False):
            return []
        return [('id', 'in', self.env.context.get('domain_product_tmpl_ids', []))]

    product_id = fields.Many2one('product.product', string='Product Variant', domain=_domain_product)
    product_tmpl_id = fields.Many2one('product.template', string='Product', domain=_domain_product_tmpl)

    def action_confirm(self):
        context = self.env.context.copy()
        if self.product_id:
            context.update({
                'default_product_id': self.product_id.id
            })
        if self.product_tmpl_id:
            context.update({
                'default_product_tmpl_id': self.product_tmpl_id.id
            })
        return {
            'name': _('Pick Product To Replenish'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.replenish',
            'target': 'new',
            'view_mode': 'form',
            'context': context,
        }
