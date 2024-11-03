from odoo import models, fields, api

class ReportInvoiceWithoutPayment(models.AbstractModel):
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super(ReportInvoiceWithoutPayment, self)._get_report_values(docids, data)
        for res in rslt['docs']:
            if res.amount_by_group:
                res.update({'amount_by_group': []})
        return rslt

class ReportInvoiceWithPayment(models.AbstractModel):
    _inherit = 'report.account.report_invoice_with_payments'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super(ReportInvoiceWithPayment, self)._get_report_values(docids, data)
        for res in rslt['docs']:
            if res.amount_by_group:
                res.update({'amount_by_group': []})
        return rslt
