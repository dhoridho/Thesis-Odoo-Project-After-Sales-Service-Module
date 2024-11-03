from odoo import _, api, fields, models



class equip3WhatsappMessageTemplate(models.Model):
    _name = 'whatsapp.template.message'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Whatsapp Template'

    @api.model
    def _default_get_broadcast_template(self):
        template_id = self.env['qiscus.wa.template'].search([('name', '=','hm_notification_template')])
        if template_id:
            content_id = self.env['qiscus.wa.template.content'].search([('template_id', '=', template_id.id), ('language', '=', 'en')])
            if content_id:
                return content_id
            else:
                return False
        else:
            return False

    name = fields.Char()
    message = fields.Text()
    broadcast_template_id = fields.Many2one('qiscus.wa.template.content', string="Broadcast Template", default=_default_get_broadcast_template)
    namespace = fields.Char(related='broadcast_template_id.template_id.namespace') 
    content = fields.Text(related='broadcast_template_id.content')
    wa_variable_ids = fields.One2many('whatsapp.template.message.variable', 'wa_id')

    def action_test_template(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.test.template',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Whatsapp Test Template",
            'context': {'default_wa_id': self.id, 'default_broadcast_template_id': self.broadcast_template_id.id},
            'target': 'new',
        }

    
    

    @api.model
    def default_get(self, fields):
        res = super(equip3WhatsappMessageTemplate, self).default_get(fields)
        line_list = []
        line_list.append((0, 0, {'name': "${approver_name}",
                                 'description': "Approver Name"
                                 }))
        line_list.append((0, 0, {'name': "${submitter_name}",
                                 'description': "Submitter Name"
                                 }))
        line_list.append((0, 0, {'name': "${currency}",
                                 'description': "Currency"
                                 }))
        line_list.append((0, 0, {'name': "${partner_name}",
                                 'description': "Partner Name"
                                 }))
        line_list.append((0, 0, {'name': "${due_date}",
                                 'description': "Due Date"
                                 }))
        line_list.append((0, 0, {'name': "${date_invoice}",
                                 'description': "Invoice Date"
                                 }))
        line_list.append((0, 0, {'name': "${url}",
                                 'description': "Url Of The Approval Request"
                                 }))
        line_list.append((0, 0, {'name': "${create_date}",
                                 'description': "Create Date"
                                 }))
        line_list.append((0, 0, {'name': "${feedback}",
                                 'description': "Feedback"
                                 }))
        line_list.append((0, 0, {'name': "${bank_from}",
                                 'description': "Bank From"
                                 }))
        line_list.append((0, 0, {'name': "${bank_to}",
                                 'description': "Bank To"
                                 }))
        line_list.append((0, 0, {'name': "${transfer_date}",
                                 'description': "Transfer Date"
                                 }))
        line_list.append((0, 0, {'name': "${bank}",
                                 'description': "Bank"
                                 }))
        line_list.append((0, 0, {'name': "${payee_name}",
                                 'description': "Name Of Payee"
                                 }))
        line_list.append((0, 0, {'name': "${amount_currency}",
                                 'description': "Amount In Currency"
                                 }))
        line_list.append((0, 0, {'name': "${date_purchase_currency}",
                                 'description': "Date Currency Purchased"
                                 }))
        line_list.append((0, 0, {'name': "${rejecter_user}",
                                 'description': "Rejecter User"
                                 }))
        line_list.append((0, 0, {'name': "${custodian_name}",
                                 'description': "Custodian"
                                 }))
        line_list.append((0, 0, {'name': "${fund_name}",
                                 'description': "Fund"
                                 }))
        line_list.append((0, 0, {'name': "${voucher_date}",
                                 'description': "Voucher Date"
                                 }))
        line_list.append((0, 0, {'name': "${voucher_name}",
                                 'description': "Voucher Name"
                                 }))
        line_list.append((0, 0, {'name': "${total_amount}",
                                 'description': "Amount Total"
                                 }))
        line_list.append((0, 0, {'name': "${amount}",
                                 'description': "Amount"
                                 }))
        line_list.append((0, 0, {'name': "${payment_date}",
                                 'description': "Payment Date"
                                 }))
        res.update({'wa_variable_ids': line_list})
        return res


    @api.model
    def create(self, vals_list):
        res = super(equip3WhatsappMessageTemplate, self).create(vals_list)
        line_list = []
        line_list.append((0, 0, {'name': "${approver_name}",
                                 'description': "Approver Name"
                                 }))
        line_list.append((0, 0, {'name': "${submitter_name}",
                                 'description': "Submitter Name"
                                 }))
        line_list.append((0, 0, {'name': "${currency}",
                                 'description': "Currency"
                                 }))
        line_list.append((0, 0, {'name': "${partner_name}",
                                 'description': "Partner Name"
                                 }))
        line_list.append((0, 0, {'name': "${due_date}",
                                 'description': "Due Date"
                                 }))
        line_list.append((0, 0, {'name': "${date_invoice}",
                                 'description': "Invoice Date"
                                 }))
        line_list.append((0, 0, {'name': "${url}",
                                 'description': "Url Of The Approval Request"
                                 }))
        line_list.append((0, 0, {'name': "${create_date}",
                                 'description': "Create Date"
                                 }))
        line_list.append((0, 0, {'name': "${feedback}",
                                 'description': "Feedback"
                                 }))
        line_list.append((0, 0, {'name': "${bank_from}",
                                 'description': "Bank From"
                                 }))
        line_list.append((0, 0, {'name': "${bank_to}",
                                 'description': "Bank To"
                                 }))
        line_list.append((0, 0, {'name': "${transfer_date}",
                                 'description': "Transfer Date"
                                 }))
        line_list.append((0, 0, {'name': "${bank}",
                                 'description': "Bank"
                                 }))
        line_list.append((0, 0, {'name': "${payee_name}",
                                 'description': "Name Of Payee"
                                 }))
        line_list.append((0, 0, {'name': "${amount_currency}",
                                 'description': "Amount In Currency"
                                 }))
        line_list.append((0, 0, {'name': "${date_purchase_currency}",
                                 'description': "Date Currency Purchased"
                                 }))
        line_list.append((0, 0, {'name': "${rejecter_user}",
                                 'description': "Rejecter User"
                                 }))
        line_list.append((0, 0, {'name': "${custodian_name}",
                                 'description': "Custodian"
                                 }))
        line_list.append((0, 0, {'name': "${fund_name}",
                                 'description': "Fund"
                                 }))
        line_list.append((0, 0, {'name': "${voucher_date}",
                                 'description': "Voucher Date"
                                 }))
        line_list.append((0, 0, {'name': "${voucher_name}",
                                 'description': "Voucher Name"
                                 }))
        line_list.append((0, 0, {'name': "${total_amount}",
                                 'description': "Amount Total"
                                 }))
        line_list.append((0, 0, {'name': "${amount}",
                                 'description': "Amount"
                                 }))
        line_list.append((0, 0, {'name': "${payment_date}",
                                 'description': "Payment Date"
                                 }))

        if not res.wa_variable_ids:
            res.wa_variable_ids = line_list
        return res


class equip3WhatsappMessageTemplateVariables(models.Model):
    _name = 'whatsapp.template.message.variable'
    _description = 'whatsapp Template'

    wa_id = fields.Many2one('whatsapp.template.message', ondelete='cascade')
    name = fields.Char()
    description = fields.Char()

