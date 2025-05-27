from odoo import models, fields, api
from odoo.exceptions import UserError

class Employee(models.Model):
    _inherit = 'hr.employee'

    # user_id = fields.Many2one('res.users', string="User", ondelete='set null')

    ongoing_tasks = fields.Integer(compute='_compute_ongoing_tasks', string="Ongoing Tasks")

    def action_create_user(self):
        """Create a user for this employee."""
        for employee in self:
            if not employee.user_id:
                # Default group assignment
                groups = [self.env.ref('base.group_user').id]
                if employee.job_id.name in ['Customer Service', 'Technician']:
                    groups.append(self.env.ref('after_sales_service.group_after_sales_team').id)
                    if employee.job_id.name == 'Customer Service':
                        groups.append(self.env.ref('after_sales_service.group_customer_service').id)
                    elif employee.job_id.name == 'Technician':
                        groups.append(self.env.ref('after_sales_service.group_technician').id)

                # Create the user
                user = self.env['res.users'].create({
                    'name': employee.name,
                    'login': employee.work_email or employee.name.lower().replace(' ', ''),
                    'password': '123',
                    'partner_id': employee.address_home_id.id if employee.address_home_id else None,
                    'groups_id': [(6, 0, groups)],  # Assign groups dynamically
                })
                # Link the user to the employee
                employee.user_id = user.id

    @api.model
    def create(self, vals):
        employee = super(Employee, self).create(vals)
        if employee.job_id:
            employee._update_user_groups_based_on_job()
        return employee

    def write(self, vals):
        res = super(Employee, self).write(vals)
        if 'job_id' in vals:
            self._update_user_groups_based_on_job()
        return res

    def _update_user_groups_based_on_job(self):
        for employee in self:
            if not employee.user_id:
                continue

            # Get all relevant groups
            after_sales_team = self.env.ref('after_sales_service.group_after_sales_team')
            customer_service = self.env.ref('after_sales_service.group_customer_service')
            technician = self.env.ref('after_sales_service.group_technician')

            # Remove all these groups first to avoid duplicates
            employee.user_id.groups_id -= (after_sales_team | customer_service | technician)

            # Add groups based on job position
            if employee.job_id:
                if employee.job_id.name.lower() == 'customer service':
                    employee.user_id.groups_id = [(4, after_sales_team.id), (4, customer_service.id)]
                elif employee.job_id.name.lower() == 'technician':
                    employee.user_id.groups_id = [(4, after_sales_team.id), (4, technician.id)]

    def _compute_ongoing_tasks(self):
        for rec in self:
            rec.ongoing_tasks = self.env['repair.history'].search_count([
                ('technician_id', '=', rec.id),
                ('state', 'in', ['pending', 'in_progress'])
            ])

    def action_select_technician(self):
        technician_id = self.id
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'service.request':
            rec = self.env['service.request'].browse(active_id)
        elif active_model == 'warranty.claim':
            rec = self.env['warranty.claim'].browse(active_id)
        else:
            raise UserError("Unknown model for assignment.")

        rec.technician_id = technician_id

        return {'type': 'ir.actions.act_window_close'}

    def action_select_technician_server(self):
        """Method to handle technician selection from the wizard tree"""
        wizard_id = self.env.context.get('wizard_id')
        technician_id = self.id  # Current technician record ID

        if wizard_id and technician_id:
            wizard = self.env['technician.assign.wizard'].browse(wizard_id)
            wizard.selected_technician_id = technician_id

        return {'type': 'ir.actions.act_window_close'}

