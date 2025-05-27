from odoo import api, models, fields


class ServiceRequestReportParser(models.AbstractModel):
    _name = 'report.after_sale_report.report_service_request_template'
    _description = 'Service Request Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        if not data:
            raise ValueError("Missing report data.")

        report_data = data['form'].get('report_data', 'service_request')
        model_map = {
            'service_request': 'service.request',
            'warranty_claim': 'warranty.claim',
            'sale_return': 'dev.rma.rma'
        }
        model_name = model_map.get(report_data, 'service.request')

        records = self.env[model_name].browse(data.get('ids', []))

        return {
            'doc_ids': docids,
            'doc_model': model_name,
            'docs': records,
            'data': data,
        }

    def get_report_filename(self, docids, data):
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


class WarrantyClaimReportParser(models.AbstractModel):
    _name = 'report.after_sale_report.report_warranty_claim_template'
    _description = 'Warranty Claim Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        if not data:
            data = {'form': {
                'start_date': False,
                'end_date': False,
                'user_type': 'both',
                'responsible_id': False,
                'ids': docids
            }}

        # Get the records
        warranty_claims = self.env['warranty.claim'].browse(data.get('ids', []))

        return {
            'doc_ids': docids,
            'doc_model': 'warranty.claim',
            'docs': warranty_claims,
            'data': data,
        }


class SaleReturnReportParser(models.AbstractModel):
    _name = 'report.after_sale_report.report_sale_return_template'
    _description = 'Sale Return Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        if not data:
            data = {'form': {
                'start_date': False,
                'end_date': False,
                'user_type': 'both',
                'responsible_id': False,
                'ids': docids
            }}

        # Get the records
        sale_returns = self.env['dev.rma.rma'].browse(data.get('ids', []))

        return {
            'doc_ids': docids,
            'doc_model': 'dev.rma.rma',
            'docs': sale_returns,
            'data': data,
        }


class TechnicianTaskReportParser(models.AbstractModel):
    _name = 'report.after_sale_report.report_technician_task_template'
    _description = 'Technician Task Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        if not data:
            # Initialize with default values if no data is provided
            data = {
                'form': {
                    'start_date': False,
                    'end_date': False,
                    'technician_id': False,
                    'technician_name': "All Technicians",
                    'all_technicians': True,
                    'technician_data': {},
                    'report_date': fields.Date.today(),
                }
            }

        # Ensure all required keys exist in the form dictionary
        form_data = data.get('form', {})
        data['form'] = {
            'start_date': form_data.get('start_date', False),
            'end_date': form_data.get('end_date', False),
            'technician_id': form_data.get('technician_id', False),
            'technician_name': form_data.get('technician_name', "All Technicians"),
            'all_technicians': form_data.get('all_technicians', True),
            'technician_data': form_data.get('technician_data', {}),
            'report_date': form_data.get('report_date', fields.Date.today()),
        }

        return {
            'doc_ids': docids,
            'doc_model': 'technician.task.report.wizard',
            'docs': self.env['technician.task.report.wizard'].browse(docids),
            'data': data,
        }