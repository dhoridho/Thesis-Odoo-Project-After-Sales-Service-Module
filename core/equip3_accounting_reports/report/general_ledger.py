from odoo import api, models, _

class GeneralLedger(models.AbstractModel):
    _inherit = 'report.dynamic_accounts_report.general_ledger'

    @api.model
    def _get_report_values(self, docids, data=None):
        result = super(GeneralLedger, self)._get_report_values(docids, data=data)
        return data

