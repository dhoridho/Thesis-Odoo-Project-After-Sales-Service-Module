from odoo import models, fields


class KsActionsSalesForecastReport(models.Model):
    _name = 'ks.sales.forecast.report'
    _description = 'Sale Forecast Report'
    _inherit = 'ir.actions.actions'
    _table = 'ks_report_actions'

    type = fields.Char(default='ks.sales.forecast.report')

    def _get_readable_fields(self):
        # data is not a stored field, but is used to give the parameters to generate the report
        # We keep it this way to ensure compatibility with the way former version called this action.
        return super()._get_readable_fields() | {'data'}
