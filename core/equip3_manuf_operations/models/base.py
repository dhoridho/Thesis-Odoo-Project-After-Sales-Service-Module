from odoo import models, api
from odoo.osv import expression


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _search_panel_domain_image(self, field_name, domain, set_count=False, limit=False):
        field = self._fields[field_name]
        if self._name != 'mrp.plan' or field.type != 'many2many' or field_name != 'product_ids':
            return super(Base, self)._search_panel_domain_image(field_name, domain, set_count=set_count, limit=limit)

        production_ids = self.env['mrp.production'].search([('mrp_plan_id', '!=', False)])
        domain = expression.AND([domain, [('id', 'in', production_ids.mapped('mrp_plan_id').ids)]])
        plan_ids = self.search(domain)
        
        domain_image = {}
        for plan in plan_ids:
            product_ids = production_ids.filtered(lambda p: p.mrp_plan_id == plan).mapped('product_id')
            for product in product_ids:
                domain_image[product.id] = {
                    'id': product.id, 
                    'display_name': product.display_name
                }
        return domain_image
