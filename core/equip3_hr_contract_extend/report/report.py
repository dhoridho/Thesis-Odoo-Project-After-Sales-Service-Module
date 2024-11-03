from odoo import models, api
from odoo.exceptions import ValidationError


class contract_letter_report(models.AbstractModel):
    _name = 'report.equip3_hr_contract_extend.contract_letter_template'
    _description = 'Contract Letter Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        contract = self.env['hr.contract'].browse(docids)
        if not contract.contract_template:
            raise ValidationError("Sorry, you can't print the contract because the contract letter template is empty.")
        if not contract.date_end:
            raise ValidationError("Sorry, you can't print the contract because the End Date fields is empty.")
        return {
            'doc_ids': docids,
            'docs': contract,
            'doc_model': 'hr.contract',
        }
