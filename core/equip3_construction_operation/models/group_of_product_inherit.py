from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GroupOfProduct(models.Model):
    _inherit = 'group.of.product'

    is_carry_over = fields.Boolean(string='Auto carry over budget', default=True)

    def update_gop_product(self):
        query_statement = """
        insert into product_gop_rel(gop_id, product_template_id)
        select distinct gop_id, product_template_id
        from(

            select gop_id, product_tmpl_id as product_template_id 
            from (
                select group_of_product as gop_id, product_id from material_estimate_template union
                select group_of_product as gop_id, product_id from labour_estimate_template union
                select group_of_product as gop_id, product_id from overhead_estimate_template union
                select group_of_product as gop_id, product_id from equipment_estimate_template union

                select group_of_product as gop_id, product_id from material_estimate union
                select group_of_product as gop_id, product_id from labour_estimate union
                select group_of_product as gop_id, product_id from overhead_estimate union
                select group_of_product as gop_id, product_id from equipment_estimate union

                select group_of_product as gop_id, product_id from budget_material union
                select group_of_product as gop_id, product_id from budget_labour union
                select group_of_product as gop_id, product_id from budget_overhead union
                select group_of_product as gop_id, product_id from budget_equipment
            ) x 
            inner join product_product on x.product_id = product_product.id

        ) as y
        WHERE NOT EXISTS (
            SELECT 1
            FROM product_gop_rel
            WHERE product_gop_rel.gop_id = y.gop_id
            AND product_gop_rel.product_template_id = y.product_template_id
        );
        """
        self.sudo().env.cr.execute(query_statement)
        return True
