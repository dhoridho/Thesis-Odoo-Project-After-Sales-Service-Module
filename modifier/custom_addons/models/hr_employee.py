from odoo import models, fields


class Employee(models.Model):
    _inherit = 'hr.employee'

    # user_id = fields.Many2one('res.users', string="User", ondelete='set null')

    def action_create_user(self):
        """Create a user for this employee."""
        for employee in self:
            if not employee.user_id:
                user = self.env['res.users'].create({
                    'name': employee.name,
                    'login': employee.work_email or employee.name.lower().replace(' ', ''),
                    'partner_id': employee.address_home_id.id if employee.address_home_id else None,
                    'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],  # Assign a default internal user group
                })
                employee.user_id = user.id
