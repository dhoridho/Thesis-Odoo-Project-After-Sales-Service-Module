
from odoo import api , fields , models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    cancel_receipt = fields.Boolean("Cancel Receipt", default=True)
    cancel_bill = fields.Boolean("Cancel Bill and Payment", default=True)

    @api.model
    def _default_report_pr_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.request'), ('report_name', '=', 'equip3_purchase_operation.report_purchase_request_custom_exclusive')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.request')])[0]
        return report_id

    report_pr_template_id = fields.Many2one('ir.actions.report', string="Purchase Request Template",  default=_default_report_pr_template,
                                            help="Please select Template report for Purchase Request", domain=[('model', '=', 'purchase.request')])

    @api.model
    def _assign_purchase_request_template(self):
        companies = self.search([])
        for company in companies:
            report_id = self._default_report_pr_template()
            company.report_pr_template_id = report_id
