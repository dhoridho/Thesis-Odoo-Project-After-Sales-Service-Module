from odoo import api, models

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    @api.model
    def get_empty_list_help(self, help_message):
        if help_message:
            help_message = str(help_message)
        else:
            help_message = ''
        return super(HrExpense, self).get_empty_list_help(str(help_message) + self._get_empty_list_mail_alias())