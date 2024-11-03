from odoo import api , models, fields 
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

class RetentionClaimConfirmation(models.TransientModel):
    _name = 'retention.claim.confirmation.wiz'
    _description = 'Retention Confirmation Wizard'

    warning_text = fields.Text(string='Confirmation', compute='_compute_warning')
    progressive_bill = fields.Boolean('Progressive Bill')
    progressive_claim_id = fields.Many2one('progressive.claim', string="Progressive Claim")
    approved_progress = fields.Float(string='Approved Progress')
    invoiced_progress = fields.Float(string='Invoiced Progress', digits=(2,2))
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
    tax_id = fields.Many2many('account.tax', 'taxes3', string="Taxes")
    last_progress = fields.Float('Last Invoice Progress', digits=(2,2))
    last_amount = fields.Float('Last Invoice Amount')

    @api.depends('progressive_claim_id', 'progressive_bill', 'invoice_for')
    def _compute_warning(self):
        claim = self.progressive_claim_id
        if self.progressive_bill == False:
            contract = claim.contract_parent
        else:
            contract = claim.contract_parent_po
            
        retention_term = contract.retention_term_1
        day_term = retention_term.days

        if claim.complete_progress == False:
            full_progress = self.env['project.claim'].search([('claim_id', '=', claim.id), ('claim_for', '=', 'progress'), ('progressline', '=', 100)], limit=1)
        else:
            full_progress = self.env['project.claim'].search([('claim_id', '=', claim.id)], limit=1, order='create_date desc')
        
        retention_1 = self.env['project.claim'].search([('claim_id', '=', claim.id), ('claim_for', '=', 'retention1')], limit=1)
         
        if self.invoice_for == 'retention1':
            date_progress = full_progress.date
        elif self.invoice_for == 'retention2':
            date_progress = retention_1.date

        invoice_date = date_progress + relativedelta(days=+(day_term))
        
        current_day = (invoice_date).day
        current_month = (invoice_date).month
        current_year = (invoice_date).year

        if self.progressive_bill == False:
            if self.invoice_for == 'retention1':
                temp_warning = f"Retention 1 should be invoiced on {datetime(current_year, current_month, current_day).strftime('%d/%m/%Y')}.\nAre you sure you want to create this invoice earlier?"
            elif self.invoice_for == 'retention2': 
                temp_warning = f"Retention 2 should be invoiced on {datetime(current_year, current_month, current_day).strftime('%d/%m/%Y')}.\nAre you sure you want to create this invoice earlier?"
        else:
            if self.invoice_for == 'retention1':
                temp_warning = f"Retention 1 should be billed on {datetime(current_year, current_month, current_day).strftime('%d/%m/%Y')}.\nAre you sure you want to create this bill earlier?"
            elif self.invoice_for == 'retention2': 
                temp_warning = f"Retention 2 should be billed on {datetime(current_year, current_month, current_day).strftime('%d/%m/%Y')}.\nAre you sure you want to create this bill earlier?"
                
        self.warning_text = temp_warning
    
    def action_confirm(self):
        claim_id_unpaid = self.env['project.claim'].search([('claim_id', '=', self.progressive_claim_id.id), ('payment_status', '!=', 'paid')])
    
        if self.invoice_for == 'retention1':
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
                       }


        if len(claim_id_unpaid) == 0:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'progressive.invoice.wiz',
                'name': "Create Progressive Invoice",
                "context": context,
                'target': 'new',
                'view_type': 'form',
                'view_mode': 'form',
                }
        elif len(claim_id_unpaid) > 0:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'res_model': 'unpaid.confirmation.wiz',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                "context": context
            }