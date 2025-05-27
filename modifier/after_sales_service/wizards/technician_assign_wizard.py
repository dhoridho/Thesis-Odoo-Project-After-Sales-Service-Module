from odoo import models, fields, api
from odoo.exceptions import UserError


class TechnicianAssignWizard(models.TransientModel):
    _name = 'technician.assign.wizard'
    _description = 'Technician Assignment Wizard'

    service_request_id = fields.Many2one('service.request', string="Service Request")
    warranty_claim_id = fields.Many2one('warranty.claim', string="Warranty Claim")
    selected_technician_id = fields.Many2one('hr.employee', string="Selected Technician")
    technician_line_ids = fields.One2many('technician.assign.wizard.line', 'wizard_id', string="Available Technicians")

    @api.model
    def default_get(self, fields_list):
        res = super(TechnicianAssignWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'service.request':
            res['service_request_id'] = active_id
        elif active_model == 'warranty.claim':
            res['warranty_claim_id'] = active_id

        # Create wizard lines for available technicians
        technicians = self.env['hr.employee'].search([
            ('job_title', 'in', ['Technician', 'Technician Manager'])
        ])

        technician_lines = []
        for tech in technicians:
            technician_lines.append((0, 0, {
                'technician_id': tech.id,
                'name': tech.name,
                'job_title': tech.job_title,
                'ongoing_tasks': tech.ongoing_tasks,
            }))

        res['technician_line_ids'] = technician_lines
        return res

    def action_assign(self):
        """Assign the selected technician"""
        if not self.selected_technician_id:
            raise UserError("Please select a technician first.")

        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')

        if active_model == 'service.request':
            service_request = self.env['service.request'].browse(active_id)
            service_request.technician_id = self.selected_technician_id.id
        elif active_model == 'warranty.claim':
            warranty_claim = self.env['warranty.claim'].browse(active_id)
            warranty_claim.technician_id = self.selected_technician_id.id
        else:
            raise UserError("Invalid context for technician assignment.")

        return {'type': 'ir.actions.act_window_close'}

    def action_select_technician(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class TechnicianAssignWizardLine(models.TransientModel):
    _name = 'technician.assign.wizard.line'
    _description = 'Technician Assignment Wizard Line'

    wizard_id = fields.Many2one('technician.assign.wizard', string="Wizard", ondelete='cascade')
    technician_id = fields.Many2one('hr.employee', string="Technician", required=True)
    name = fields.Char(string="Technician Name", related='technician_id.name', readonly=True)
    job_title = fields.Char(string="Job Title", related='technician_id.job_title', readonly=True)
    ongoing_tasks = fields.Integer(string="Ongoing Tasks", related='technician_id.ongoing_tasks', readonly=True)

    def action_select_technician(self):
        """Select this technician and update wizard"""
        if self.wizard_id and self.technician_id:
            self.wizard_id.selected_technician_id = self.technician_id
            # Force refresh the wizard view
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return True

    def button_test(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}