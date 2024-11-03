from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class UnpaidConfirmation(models.TransientModel):
    _name = 'unpaid.confirmation.wiz'
    _description = 'Confirmation Unpaid Invoice'

    txt_inv = fields.Text(string="Confirmation",default="It looks like there are still unpaid invoices. Are you sure to create another invoice?")
    txt_bill = fields.Text(string="Confirmation",default="It looks like there are still unpaid bills. Are you sure to create another bill?")
    progressive_bill = fields.Boolean('Progressive Bill')
    progressive_claim_id = fields.Many2one('progressive.claim', string="Progressive Claim")
    approved_progress = fields.Float(string='Approved Progress')
    invoiced_progress = fields.Float(string = 'Invoiced Progress', digits=(2,2))
    invoice_for = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Invoice Type')
    contract_amount = fields.Float(string='Contract Amount')
    down_payment = fields.Float(string="Down Payment")
    dp_amount = fields.Float(string="Amount")
    retention1 = fields.Float(string="Retention 1")
    retention2 = fields.Float(string="Retention 2")
    retention1_amount = fields.Float(string="Amount")
    retention2_amount = fields.Float(string="Amount")
    tax_id = fields.Many2many('account.tax', 'taxes2', string="Taxes")
    last_progress = fields.Float('Last Invoice Progress', digits=(2,2))
    last_amount = fields.Float('Last Invoice Amount')
    milestone_id = fields.Many2one('account.milestone.term.const', string="Milestone")


    def action_confirm(self):
        if self.invoice_for == 'down_payment':
            context = {'default_invoice_for': 'down_payment',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.dp_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment' : self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_last_progress': self.last_progress,
                       'default_last_amount': self.last_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.progressive_claim_id.id,
                       'default_milestone_id': self.milestone_id.id if self.milestone_id else False,
                       }
        
        elif self.invoice_for == 'progress':
            context = {'default_invoice_for': 'progress',
                       'default_progressive_bill': self.progressive_bill,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_last_progress': self.invoiced_progress,
                       'default_last_amount': self.last_amount,
                       'default_down_payment' : self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.progressive_claim_id.id,
                       'default_milestone_id': self.milestone_id.id if self.milestone_id else False,
                       }

        elif self.invoice_for == 'retention1':
            context = {'default_invoice_for': 'retention1',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.retention1_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment' : self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.progressive_claim_id.id,
                       'default_milestone_id': self.milestone_id.id if self.milestone_id else False,
                       }
        
        elif self.invoice_for == 'retention2':
            context = {'default_invoice_for': 'retention2',
                       'default_progressive_bill': self.progressive_bill,
                       'default_invoice_progress': self.retention2_amount,
                       'default_approved_progress': self.approved_progress,
                       'default_contract_amount': self.contract_amount,
                       'default_down_payment' : self.down_payment,
                       'default_dp_amount': self.dp_amount,
                       'default_retention1': self.retention1,
                       'default_retention2': self.retention2,
                       'default_retention1_amount': self.retention1_amount,
                       'default_retention2_amount': self.retention2_amount,
                       'default_tax_id': [(6, 0, [v.id for v in self.tax_id])],
                       'default_progressive_claim_id': self.progressive_claim_id.id,
                       'default_milestone_id': self.milestone_id.id if self.milestone_id else False,
                       }


        return {
            'type': 'ir.actions.act_window',
            'res_model': 'progressive.invoice.wiz',
            'name': "Create Progressive Invoice",
            'context': context,
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'form',
            }