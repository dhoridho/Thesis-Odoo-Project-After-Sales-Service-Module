from odoo import api, models, _


class PartnerAgeing(models.AbstractModel):    
    _inherit = 'report.dynamic_accounts_report.partner_ageing'

    @api.model
    def _get_report_values(self, docids, data=None):
        result = super(PartnerAgeing, self)._get_report_values(docids, data=data)
        if self.env.context.get('ageing_pdf_report'):
            if data.get('report_data'):
                result.update(
                    {'account_total': data.get('report_data')['report_lines'][1]})
        return result