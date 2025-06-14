from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_customer = fields.Boolean(string="Is Customer", default=False)


class ResUsers(models.Model):
    _inherit = "res.users"

    def action_change_home_action(self):
        # Get the dashboard action (client type)
        action = self.env['ir.actions.actions'].search([('name', '=', 'After Sales Dashboard Action')], limit=1).id

        if not action:
            return

        for user in self:
            # Exclude admin (user ID 1)
            if user.id == 1 or user.id == 2:
                continue

            # Apply only to users in the desired group
            if user.has_group('after_sales_service.group_after_sales_team'):
                user.action_id = action
