from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_details = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash')
        ], string="Payment Details")
    amount = fields.Float(string="Amount")
    date_of_receipt = fields.Date(string="Date of Receipt")
    proof_of_payment = fields.Binary(string='Proof of Payment')
    proof_of_payment_filename = fields.Char(string='Proof of Payment Filename')
    receipt_number = fields.Char(string="Receipt Number")
    remarks = fields.Text(string="Remarks")

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for rec in self:
            if rec.state == 'posted' and rec.payment_state == 'paid' and rec.student_payslip_id:
                rec.student_payslip_id.payslip_paid()
        return res

    def action_register_payment(self):
        action = super(AccountMove, self).action_register_payment()
        action["context"] = {
            'active_model': 'account.move',
            'active_ids': self.ids,
            'default_branch_id': self.branch_id.id
        }

        return action
