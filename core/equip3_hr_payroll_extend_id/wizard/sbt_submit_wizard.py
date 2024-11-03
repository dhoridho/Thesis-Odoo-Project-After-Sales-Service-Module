from odoo import fields, models, api, _

class HrSplitBankTransferSubmitWizard(models.TransientModel):
    _name = 'hr.split.bank.transfer.submit.wizard'
    _description = "HR Split Bank Transfer Submit Wizard"

    message = fields.Text(string="Text", default="Total amount is smaller then the Maximum Amount to Split. Are you sure to continue the transaction?")
    split_id = fields.Many2one('hr.split.bank.transfer')

    def action_continue(self):
        self.split_id.submit()

