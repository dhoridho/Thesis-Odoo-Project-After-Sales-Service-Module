from odoo import api, fields, models, _

class PosCategory(models.Model):
    _inherit = "pos.category"

    def get_all_child_categories(self, category, all_child_categories=None):
        # get all child categories recursively
        child_categories = self.env['pos.category'].sudo().search([('parent_id', '=', category.id)])
        all_child_categories = child_categories
        
        for child_category in child_categories:
            all_child_categories += child_category.get_all_child_categories(child_category)
        return all_child_categories