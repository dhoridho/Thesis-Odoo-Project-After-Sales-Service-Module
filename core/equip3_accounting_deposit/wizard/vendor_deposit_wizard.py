# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class WizardVendorDeposit(models.TransientModel):
    _name = "wizard.vendor.deposit"
    _description = 'Wizard Vendor Deposit'

    reason = fields.Text(string="Reason")
    add_amount = fields.Boolean(string="add amount")

    def action_reject(self):
        vendor_deposit_id = self.env['vendor.deposit'].browse([self._context.get('active_id')])
        user = self.env.user
        # if self.add_amount == True:
        #     approving_matrix_line = sorted(vendor_deposit_id.approved_matrix_ids.filtered(lambda r: r.approved), key=lambda r:r.sequence)
        # else:
        #     approving_matrix_line = sorted(vendor_deposit_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        approving_matrix_line = sorted(vendor_deposit_id.approved_matrix_ids.filtered(lambda r: r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            action_id = self.env.ref('equip3_accounting_deposit.action_vendor_deposit')
            template_id = self.env.ref('equip3_accounting_deposit.email_template_vendor_deposit_rejected_matrix')
            wa_template_id = self.env.ref('equip3_accounting_deposit.wa_template_vendor_deposit_rejected_matrix')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(vendor_deposit_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=vendor.deposit'
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : vendor_deposit_id.request_partner_id.email,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': vendor_deposit_id.create_date.date(),
                'date': vendor_deposit_id.create_date.date(),
            }
            template_id.with_context(ctx).send_mail(vendor_deposit_id.id, True)
            # vendor_deposit_id._send_whatsapp_message(wa_template_id, vendor_deposit_id.request_partner_id.user_ids, url=url, reason=self.reason)
            if vendor_deposit_id.is_allowed_to_wa_notification_vendor_deposit:
                vendor_deposit_id._send_wa_reject_vendor_deposit(vendor_deposit_id.request_partner_id.name, vendor_deposit_id.request_partner_id.mobile, vendor_deposit_id.create_date.date(), self.env.user.name, self.reason)
            list_approval = self.env['vendor.deposit.approval.line'].browse([self._context.get('id_approval')])
            list_approval.write({'approve' : True})
            vendor_deposit_id.write({'deposit_count': vendor_deposit_id.deposit_count-1})
            # if vendor_deposit_id.deposit_count == 0:
            #     vendor_deposit_id.state = 'rejected'
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'vendor.deposit',
                'view_mode': 'form',
                'res_id': vendor_deposit_id.id,
            }
            return action
            