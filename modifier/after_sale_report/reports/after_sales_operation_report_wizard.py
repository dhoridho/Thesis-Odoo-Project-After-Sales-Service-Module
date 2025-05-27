import base64
import io
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import xlsxwriter

class AfterSalesOperationReportWizard(models.TransientModel):
    _name = 'after.sales.operation.report.wizard'
    _description = 'After Sales Operation Report Wizard'

    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    user_type = fields.Selection([
        ('responsible', 'Customer Service'),
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

        date_domain = []
        if self.start_date:
            date_domain.append(('create_date', '>=', self.start_date))
        if self.end_date:
            date_domain.append(('create_date', '<=', self.end_date))


        # Select the appropriate report generation method based on format and report_data
        if self.report_type == 'xlsx':
            if self.report_data == 'service_request':
                return self._generate_service_request_excel(date_domain)
            elif self.report_data == 'warranty_claim':
                return self._generate_warranty_claim_excel(date_domain)
            elif self.report_data == 'sale_return':
                return self._generate_sale_return_excel(date_domain)
        else:
            return self._print_service_request_report(date_domain)
            # elif self.report_data == 'warranty_claim':
            #     return self._print_warranty_claim_report(date_domain)
            # elif self.report_data == 'sale_return':
            #     return self._print_sale_return_report(date_domain)

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

        # Prepare data for the report
        if self.report_data == 'service_request':
            service_requests = self._get_domain_and_records('service.request', date_domain)
            data = {
                'ids': service_requests.ids,
                'model': 'service.request',
                'form': {
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'user_type': self.user_type,
                    'responsible_id': self.responsible_id.id if self.responsible_id else False,
                    'report_data': self.report_data,
                }
            }
        elif self.report_data == 'warranty_claim':
            warranty_claims = self._get_domain_and_records('warranty.claim', date_domain)
            data = {
                'ids': warranty_claims.ids,
                'model': 'warranty.claim',
                'form': {
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'user_type': self.user_type,
                    'responsible_id': self.responsible_id.id if self.responsible_id else False,
                    'report_data': self.report_data,
                }
            }
        elif self.report_data == 'sale_return':
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
                    'report_data': self.report_data,
                }
            }

        action = self.env.ref('after_sale_report.action_report_service_request_pdf')

        action.write({
            'name': self.get_report_filename(data),
            'print_report_name': self.get_report_filename(data),
        })


        # Return the PDF report action
        return action.report_action(self, data=data)

    def get_report_filename(self, data=None):
        label_map = {
            'service_request': 'Service Request',
            'warranty_claim': 'Warranty Claim',
            'sale_return': 'Sale Return',
        }
        type_map = {
            'responsible': 'By Customer Service',
            'customer': 'By Customer',
            'both': 'By All',
        }

        title = label_map.get(self.report_data, 'After Sales')
        user_type = type_map.get(self.user_type, 'All Users')

        # Format date period
        if self.start_date and self.end_date:
            period = f"{self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}"
        elif self.start_date:
            period = f"From {self.start_date.strftime('%d/%m/%Y')}"
        elif self.end_date:
            period = f"Up to {self.end_date.strftime('%d/%m/%Y')}"
        else:
            period = "All Time"

        return f"{title} Report - {user_type} ({period})"

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


    def _generate_service_request_excel(self, date_domain):
        """Generate Service Request Excel report"""
        service_requests = self._get_domain_and_records('service.request', date_domain)

        # Create workbook and worksheet
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Service Requests')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        info_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': '#F2F2F2',
            'border': 1
        })

        data_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        center_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # Set column widths
        worksheet.set_column('A:A', 5)  # #
        worksheet.set_column('B:B', 20)  # Request No.
        worksheet.set_column('C:C', 25)  # Customer
        worksheet.set_column('D:D', 30)  # Product
        worksheet.set_column('E:E', 20)  # Customer Service
        worksheet.set_column('F:F', 15)  # Status
        worksheet.set_column('G:G', 15)  # Date

        # Write title
        worksheet.merge_range('A1:G1', 'Service Request Report', title_format)

        # Write report info
        row = 3
        worksheet.merge_range(f'A{row}:B{row}', 'Report Information:', info_format)
        row += 1

        # Date range
        if self.start_date and self.end_date:
            date_range = f"{self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}"
        elif self.start_date:
            date_range = f"From {self.start_date.strftime('%d/%m/%Y')}"
        elif self.end_date:
            date_range = f"Up to {self.end_date.strftime('%d/%m/%Y')}"
        else:
            date_range = "All Time"

        worksheet.write(f'A{row}', 'Date Range:', info_format)
        worksheet.write(f'B{row}', date_range, data_format)
        row += 1

        # User type
        user_type_map = {
            'responsible': 'By Customer Service',
            'customer': 'By Customer',
            'both': 'All Types'
        }
        worksheet.write(f'A{row}', 'Filter Type:', info_format)
        worksheet.write(f'B{row}', user_type_map.get(self.user_type, 'All Types'), data_format)
        row += 1

        # Responsible user
        if self.responsible_id:
            worksheet.write(f'A{row}', 'Responsible:', info_format)
            worksheet.write(f'B{row}', self.responsible_id.name, data_format)
            row += 1

        # Total records
        worksheet.write(f'A{row}', 'Total Records:', info_format)
        worksheet.write(f'B{row}', len(service_requests), data_format)
        row += 2

        # Write headers
        headers = ['#', 'Request No.', 'Customer', 'Product', 'Customer Service', 'Status', 'Date']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        # Write data
        row += 1
        for index, request in enumerate(service_requests):
            worksheet.write(row, 0, index + 1, center_format)
            worksheet.write(row, 1, request.name or '', data_format)
            worksheet.write(row, 2, request.partner_id.name or '', data_format)
            worksheet.write(row, 3, request.product_id.name or '', data_format)
            worksheet.write(row, 4, request.responsible_id.name or '', data_format)
            worksheet.write(row, 5, request.state.upper() if request.state else '', center_format)
            worksheet.write(row, 6, request.create_date.strftime('%d/%m/%Y') if request.create_date else '', center_format)
            row += 1

        workbook.close()
        output.seek(0)

        # Create attachment
        filename = self.get_report_filename() + '.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(output.read()),
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }

    def _generate_warranty_claim_excel(self, date_domain):
        """Generate Warranty Claim Excel report"""
        warranty_claims = self._get_domain_and_records('warranty.claim', date_domain)

        # Create workbook and worksheet
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Warranty Claims')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        info_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': '#F2F2F2',
            'border': 1
        })

        data_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        center_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # Set column widths
        worksheet.set_column('A:A', 5)  # #
        worksheet.set_column('B:B', 20)  # Claim No.
        worksheet.set_column('C:C', 25)  # Customer
        worksheet.set_column('D:D', 30)  # Product
        worksheet.set_column('E:E', 20)  # Customer Service
        worksheet.set_column('F:F', 15)  # Status
        worksheet.set_column('G:G', 15)  # Date

        # Write title
        worksheet.merge_range('A1:G1', 'Warranty Claim Report', title_format)

        # Write report info
        row = 3
        worksheet.merge_range(f'A{row}:B{row}', 'Report Information:', info_format)
        row += 1

        # Date range
        if self.start_date and self.end_date:
            date_range = f"{self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}"
        elif self.start_date:
            date_range = f"From {self.start_date.strftime('%d/%m/%Y')}"
        elif self.end_date:
            date_range = f"Up to {self.end_date.strftime('%d/%m/%Y')}"
        else:
            date_range = "All Time"

        worksheet.write(f'A{row}', 'Date Range:', info_format)
        worksheet.write(f'B{row}', date_range, data_format)
        row += 1

        # User type
        user_type_map = {
            'responsible': 'By Customer Service',
            'customer': 'By Customer',
            'both': 'All Types'
        }
        worksheet.write(f'A{row}', 'Filter Type:', info_format)
        worksheet.write(f'B{row}', user_type_map.get(self.user_type, 'All Types'), data_format)
        row += 1

        # Responsible user
        if self.responsible_id:
            worksheet.write(f'A{row}', 'Responsible:', info_format)
            worksheet.write(f'B{row}', self.responsible_id.name, data_format)
            row += 1

        # Total records
        worksheet.write(f'A{row}', 'Total Records:', info_format)
        worksheet.write(f'B{row}', len(warranty_claims), data_format)
        row += 2

        # Write headers
        headers = ['#', 'Claim No.', 'Customer', 'Product', 'Customer Service', 'Status', 'Date']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        # Write data
        row += 1
        for index, claim in enumerate(warranty_claims):
            worksheet.write(row, 0, index + 1, center_format)
            worksheet.write(row, 1, claim.name or '', data_format)
            worksheet.write(row, 2, claim.partner_id.name or '', data_format)
            worksheet.write(row, 3, claim.product_id.name or '', data_format)
            worksheet.write(row, 4, claim.responsible_id.name or '', data_format)
            worksheet.write(row, 5, claim.state.upper() if claim.state else '', center_format)
            worksheet.write(row, 6, claim.create_date.strftime('%d/%m/%Y') if claim.create_date else '', center_format)
            row += 1

        workbook.close()
        output.seek(0)

        # Create attachment
        filename = self.get_report_filename() + '.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(output.read()),
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }

    def _generate_sale_return_excel(self, date_domain):
        """Generate Sale Return Excel report"""
        sale_returns = self._get_domain_and_records('dev.rma.rma', date_domain)

        # Create workbook and worksheet
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Sale Returns')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter'
        })

        info_format = workbook.add_format({
            'bold': True,
            'font_size': 10,
            'bg_color': '#F2F2F2',
            'border': 1
        })

        data_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        center_format = workbook.add_format({
            'font_size': 10,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # Set column widths
        worksheet.set_column('A:A', 5)  # #
        worksheet.set_column('B:B', 20)  # Return No.
        worksheet.set_column('C:C', 25)  # Customer
        worksheet.set_column('D:D', 20)  # Order No.
        worksheet.set_column('E:E', 20)  # Customer Service
        worksheet.set_column('F:F', 15)  # Status
        worksheet.set_column('G:G', 15)  # Date

        # Write title
        worksheet.merge_range('A1:G1', 'Sale Return Report', title_format)

        # Write report info
        row = 3
        worksheet.merge_range(f'A{row}:B{row}', 'Report Information:', info_format)
        row += 1

        # Date range
        if self.start_date and self.end_date:
            date_range = f"{self.start_date.strftime('%d/%m/%Y')} to {self.end_date.strftime('%d/%m/%Y')}"
        elif self.start_date:
            date_range = f"From {self.start_date.strftime('%d/%m/%Y')}"
        elif self.end_date:
            date_range = f"Up to {self.end_date.strftime('%d/%m/%Y')}"
        else:
            date_range = "All Time"

        worksheet.write(f'A{row}', 'Date Range:', info_format)
        worksheet.write(f'B{row}', date_range, data_format)
        row += 1

        # Total records
        worksheet.write(f'A{row}', 'Total Records:', info_format)
        worksheet.write(f'B{row}', len(sale_returns), data_format)
        row += 2

        # Write headers
        headers = ['#', 'Return No.', 'Customer', 'Order No.', 'Customer Service', 'Status', 'Date']
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)

        # Write data
        row += 1
        for index, return_rec in enumerate(sale_returns):
            worksheet.write(row, 0, index + 1, center_format)
            worksheet.write(row, 1, return_rec.name or '', data_format)
            worksheet.write(row, 2, return_rec.partner_id.name or '', data_format)
            worksheet.write(row, 3, return_rec.sale_id.name or '', data_format)
            worksheet.write(row, 4, return_rec.user_id.name or '', data_format)
            worksheet.write(row, 5, return_rec.state.upper() if return_rec.state else '', center_format)
            worksheet.write(row, 6, return_rec.create_date.strftime('%d/%m/%Y') if return_rec.create_date else '', center_format)
            row += 1

        workbook.close()
        output.seek(0)

        # Create attachment
        filename = self.get_report_filename() + '.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(output.read()),
            'type': 'binary',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }