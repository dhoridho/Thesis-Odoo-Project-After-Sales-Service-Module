# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT



class AccountBudgetWizard(models.TransientModel):
    _name = "crossovered.budget.wizard"
    _description = 'Account Budget Wizard'

    reason = fields.Text(string="Reason")


    def action_reject(self):
        account_budget_id = self.env['crossovered.budget'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(account_budget_id.approved_matrix_ids.filtered(lambda r: not r.approved),
                                       key=lambda r: r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            action_id = self.env.ref('om_account_budget.act_crossovered_budget_view')
            template_id = self.env.ref('equip3_accounting_budget.email_template_rejection_of_budget')
            # wa_template_id_rejected = self.env.ref('equip3_accounting_budget.wa_template_rejection_of_budget')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(account_budget_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=crossovered.budget'
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : account_budget_id.request_partner_id.email,
                'partner_name': account_budget_id.request_partner_id.name,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': account_budget_id.create_date.date(),
                'date': date.today(),
            }
            template_id.with_context(ctx).send_mail(account_budget_id.id, True)
            account_budget_id.state = 'rejected'
            phone_num = str(account_budget_id.request_partner_id.mobile) or str(account_budget_id.request_partner_id.mobile)
            # account_budget_id._send_whatsapp_message_approval_submitter(wa_template_id_rejected, account_budget_id.request_partner_id.name, phone_num, account_budget_id.create_date.date(), self.env.user.name, self.reason)
            if account_budget_id.is_allowed_to_wa_notification:
                account_budget_id._send_wa_rejection_of_budget(account_budget_id.request_partner_id.name, phone_num, account_budget_id.create_date.date(), self.env.user.name, self.reason)
