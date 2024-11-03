from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def toggle_user_product_secret_group(self, has_secret_group=False):
        if not self:
            self = self.sudo().search([])
        secret_product_group = self.env.ref('equip3_manuf_accessright_settings.group_mrp_secret_product')
        not_secret_product_group = self.env.ref('equip3_manuf_accessright_settings.not_group_mrp_secret_product')
        for user in self:
            user_groups = user.groups_id
            if secret_product_group in user_groups and not_secret_product_group in user_groups:
                to_remove = not_secret_product_group if not has_secret_group else secret_product_group
                user.with_context(dont_toggle_group=True).write({'groups_id': [(3, to_remove.id)]})
            elif secret_product_group not in user_groups and not_secret_product_group not in user_groups:
                to_add = not_secret_product_group if has_secret_group else secret_product_group
                user.with_context(dont_toggle_group=True).write({'groups_id': [(4, to_add.id)]})

    def write(self, vals):
        secret_product_group = self.env.ref('equip3_manuf_accessright_settings.group_mrp_secret_product')
        has_groups = {}
        for user in self:
            has_groups[user.id] = secret_product_group in user.groups_id
        res = super(ResUsers, self).write(vals)
        if not self.env.context.get('dont_toggle_group'):
            for user in self:
                user.toggle_user_product_secret_group(has_secret_group=has_groups[user.id])
        return res
