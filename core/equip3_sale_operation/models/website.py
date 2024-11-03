from odoo import models, fields, api, _


class Website(models.Model):
    _inherit = 'website'

    def _prepare_sale_order_values(self, partner, pricelist):
        res = super(Website, self)._prepare_sale_order_values(partner, pricelist)
        res.update({
            'branch_id': self.env.branch.id,
            'is_single_warehouse': True,
            'warehouse_new_id': res.get('warehouse_id', False),
        })
        return res