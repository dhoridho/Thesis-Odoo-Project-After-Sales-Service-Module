from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class TechnicianTaskReportWizard(models.TransientModel):
    _name = 'technician.task.report.wizard'
    _description = 'Technician Task Report Wizard'

    start_date = fields.Date(string="Start Date", required=True, default=lambda self: fields.Date.today() - timedelta(days=30))
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.today())
    technician_id = fields.Many2one('hr.employee', string="Technician",
                                    domain=[('job_id.name', 'ilike', 'technician')])
    all_technicians = fields.Boolean(string="Report on All Technicians", default=False)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise UserError("Start Date cannot be after End Date")

    @api.onchange('all_technicians')
    def _onchange_all_technicians(self):
        """Clear technician_id when all_technicians is checked"""
        if self.all_technicians:
            self.technician_id = False

    @api.onchange('technician_id')
    def _onchange_technician_id(self):
        """Uncheck all_technicians when technician_id is selected"""
        if self.technician_id:
            self.all_technicians = False

    def _get_technician_repair_data(self):
        """Get repair history data for technician report"""
        domain = [
            ('repair_date', '>=', self.start_date),
            ('repair_date', '<=', self.end_date),
        ]

        if self.technician_id and not self.all_technicians:
            domain.append(('technician_id', '=', self.technician_id.id))
        elif not self.all_technicians and not self.technician_id:
            raise UserError("Please select a technician or check 'Report on All Technicians'")

        # Get repair history records
        repair_records = self.env['repair.history'].search(domain)

        if not repair_records:
            raise UserError("No repair records found for the selected criteria")

        # Organize data by technician
        technician_data = {}

        for repair in repair_records:
            # Skip if no technician assigned
            if not repair.technician_id:
                continue

            # Calculate days to complete
            days_to_complete = 0
            if repair.completion_date and repair.repair_date:
                delta = repair.completion_date - repair.repair_date
                days_to_complete = delta.days

            # Get source information
            source = repair.origin or "Direct Repair"

            # If technician not in dict yet, add them
            if repair.technician_id.id not in technician_data:
                technician_data[repair.technician_id.id] = {
                    'name': repair.technician_id.name,
                    'repairs': [],
                    'summary': {
                        'total': 0,
                        'completed': 0,
                        'in_progress': 0,
                        'pending': 0,
                        'warranty': 0,
                        'total_days': 0,
                        'total_completed': 0,
                    }
                }

            # Add repair data
            repair_info = {
                'reference': repair.name,
                'customer': repair.partner_id.name,
                'product': repair.product_id.name,
                'repair_type': dict(repair._fields['repair_type'].selection).get(repair.repair_type, ''),
                'source': source,
                'days_to_complete': days_to_complete,
                'state': repair.state,
                'state_name': dict(repair._fields['state'].selection).get(repair.state, ''),
                'description': repair.description or "",
                'is_warranty': repair.is_warranty_repair,
                'repair_date': repair.repair_date,
                'completion_date': repair.completion_date
            }

            # Update technician summary counts
            technician_data[repair.technician_id.id]['summary']['total'] += 1
            if repair.state == 'completed':
                technician_data[repair.technician_id.id]['summary']['completed'] += 1
                if days_to_complete > 0:
                    technician_data[repair.technician_id.id]['summary']['total_days'] += days_to_complete
                    technician_data[repair.technician_id.id]['summary']['total_completed'] += 1
            elif repair.state == 'in_progress':
                technician_data[repair.technician_id.id]['summary']['in_progress'] += 1
            elif repair.state == 'pending':
                technician_data[repair.technician_id.id]['summary']['pending'] += 1

            if repair.is_warranty_repair:
                technician_data[repair.technician_id.id]['summary']['warranty'] += 1

            technician_data[repair.technician_id.id]['repairs'].append(repair_info)

        # Calculate average completion time for each technician
        for tech_id, tech_data in technician_data.items():
            if tech_data['summary']['total_completed'] > 0:
                tech_data['summary']['avg_days'] = tech_data['summary']['total_days'] / tech_data['summary']['total_completed']
            else:
                tech_data['summary']['avg_days'] = 0

        return technician_data

    def print_report(self):
        """Generate technician task report based on selected criteria"""
        self.ensure_one()

        # Get technician repair data
        technician_data = self._get_technician_repair_data()

        # Prepare data for the report
        data = {
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'technician_id': self.technician_id.id if self.technician_id else False,
                'technician_name': self.technician_id.name if self.technician_id else "All Technicians",
                'all_technicians': self.all_technicians,
                'technician_data': technician_data,
                'report_date': fields.Date.today(),
            }
        }

        return self.env.ref('after_sale_report.action_technician_task_pdf').report_action(self, data=data)