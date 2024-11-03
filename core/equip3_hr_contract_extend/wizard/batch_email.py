from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def action_contract_email(self):
        partner_ids = []
        self.update_email_to_res_partner()
        for record in self:
            if not record.partner_id:
                raise ValidationError("Sorry, you can't send a contract letter because the employee (%s) is not mapped to related user" % record.employee_id.name)
            if not record.contract_template:
                raise ValidationError("Sorry, you can't send a contract letter. Because the Contract Template (%s) field has not been filled" % record.name)
            # if record.employee_id and record.employee_id.user_id and record.employee_id.user_id.partner_id:
            partner_ids.append(record.partner_id.id)
        return {
            'name': 'Compose Email',
            'type': 'ir.actions.act_window',
            'res_model': 'contract.batch.email.template',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_ids': [(6,0,self.ids)],
                'default_parent_ids': [(6,0,partner_ids)]
            },
        }


class ContractBatchEmailTemplate(models.TransientModel):
    _name = 'contract.batch.email.template'

    contract_ids = fields.Many2many('hr.contract', string='Contracts')
    parent_ids = fields.Many2many('res.partner', string='Recipients')
    email_template_id = fields.Many2one(comodel_name="mail.template", string="Email Template", required=True,
                                        help="This field contains the Email Template that will be used by default when sending this Email.",
                                        )
    subject = fields.Char(related='email_template_id.subject', string='Subject')

    def send_batch_email(self):
        for record in self:
            for contract in record.contract_ids:
                contract.update({
                    'email_template_id': record.email_template_id,
                })
                contract.certificate_mail()