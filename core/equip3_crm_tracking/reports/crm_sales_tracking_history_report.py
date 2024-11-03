from odoo import models, api


class ReportCRMSalesTrackingHistoryReport(models.AbstractModel):
    _name = 'report.equip3_crm_tracking.crm_sales_tracking_visit_report'
    _description = 'Salesperson Tracking History Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['crm.sales.tracking.history'].browse(docids),
            'doc_model': 'crm.sales.tracking.history',
        }
