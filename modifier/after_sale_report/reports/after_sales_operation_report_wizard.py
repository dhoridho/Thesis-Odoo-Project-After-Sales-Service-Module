from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime


class AfterSalesOperationReportWizard(models.TransientModel):
    _name = 'after.sales.operation.report.wizard'
    _description = 'After Sales Operation Report Wizard'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    user_type = fields.Selection([
        ('responsible', 'Responsible'),
        ('customer', 'Customer'),
        ('both', 'Both')
    ], string="User Type", default='responsible')
    responsible_id = fields.Many2one('res.users', string="Responsible")
    report_data = fields.Selection([
        ('service_request', 'Service Request'),
        ('warranty_claim', 'Warranty Claim'),
        ('sale_return', 'Sale Return')
    ], string="Report Type", required=True)
    report_type = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel')
    ], string="Output Format", default='pdf', required=True)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise UserError("Start Date cannot be after End Date")

    def print_report(self):
        """Generate report based on selected criteria"""
        self.ensure_one()

        # Common date domain for all report types
        date_domain = [
            ('create_date', '>=', self.start_date),
            ('create_date', '<=', self.end_date)
        ]

        # Select the appropriate report generation method based on format and report_data
        if self.report_type == 'xlsx':
            if self.report_data == 'service_request':
                return self._generate_service_request_excel(date_domain)
            elif self.report_data == 'warranty_claim':
                return self._generate_warranty_claim_excel(date_domain)
            elif self.report_data == 'sale_return':
                return self._generate_sale_return_excel(date_domain)
        else:
            if self.report_data == 'service_request':
                return self._print_service_request_report(date_domain)
            elif self.report_data == 'warranty_claim':
                return self._print_warranty_claim_report(date_domain)
            elif self.report_data == 'sale_return':
                return self._print_sale_return_report(date_domain)

        raise UserError("Please select a valid report type")

    def _get_domain_and_records(self, model, date_domain):
        """Build domain and get records for the given model"""
        domain = list(date_domain)  # Create a copy of the domain list

        # Add user filters based on selection
        if self.user_type == 'responsible' and self.responsible_id:
            domain.append(('responsible_id', '=', self.responsible_id.id))
        elif self.user_type == 'customer':
            domain.append(('partner_id', '!=', False))

        # Search for records
        records = self.env[model].search(domain)

        if not records:
            raise UserError(f"No records found matching your criteria")

        return records

    def _print_service_request_report(self, date_domain):
        """Generate Service Request PDF report"""
        service_requests = self._get_domain_and_records('service.request', date_domain)

        # Prepare data for the report
        data = {
            'ids': service_requests.ids,
            'model': 'service.request',
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'user_type': self.user_type,
                'responsible_id': self.responsible_id.id if self.responsible_id else False,
            }
        }

        # Return the PDF report action
        return self.env.ref('after_sale_report.action_report_service_request_pdf').report_action(self, data=data)

    def _print_warranty_claim_report(self, date_domain):
        """Generate Warranty Claim PDF report"""
        warranty_claims = self._get_domain_and_records('warranty.claim', date_domain)

        # Prepare data for the report
        data = {
            'ids': warranty_claims.ids,
            'model': 'warranty.claim',
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'user_type': self.user_type,
                'responsible_id': self.responsible_id.id if self.responsible_id else False,
            }
        }

        # Return the PDF report action
        return self.env.ref('after_sale_report.action_report_warranty_claim_pdf').report_action(self, data=data)

    def _print_sale_return_report(self, date_domain):
        """Generate Sale Return PDF report"""
        sale_returns = self._get_domain_and_records('dev.rma.rma', date_domain)

        # Prepare data for the report
        data = {
            'ids': sale_returns.ids,
            'model': 'dev.rma.rma',
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'user_type': self.user_type,
                'responsible_id': self.responsible_id.id if self.responsible_id else False,
            }
        }

        # Return the PDF report action
        return self.env.ref('after_sale_report.action_report_sale_return_pdf').report_action(self, data=data)
