from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class CancelConfirmationWiz(models.TransientModel):
    _name = 'cancel.claim.conf.wiz'

    txt_inv = fields.Text(string="Cancel Confirmation",default="Are you sure to cancel this progressive claim? Invoices that have been posted can still be continued.")
    txt_bill = fields.Text(string="Cancel Confirmation",default="Are you sure to cancel this progressive claim? Bill that have been posted can still be continued.")
    claim_id = fields.Many2one('progressive.claim', string='Claim ID')
    progressive_bill = fields.Boolean('Progressive Bill')
    contract_parent = fields.Many2one('sale.order.const', string="Parent Contract")
    contract_parent_po = fields.Many2one('purchase.order', string="Parent Contract") 

    def action_confirm(self):
        job_id = self.env['progressive.claim'].browse([self._context.get('active_id')])
        job_id.write({'state': 'cancel'})

        if self.progressive_bill == False:
            invoice = self.env['account.move'].search([('claim_id', '=', job_id.id), ('contract_parent', '=', self.contract_parent.id), ('state', '!=', 'posted')])
            for res in invoice:
                res.write({'state' : 'cancel'})

        if self.progressive_bill == True:
            bill = self.env['account.move'].search([('claim_id', '=', job_id.id), ('contract_parent_po', '=', self.contract_parent_po.id), ('state', '!=', 'posted')])
            for res in bill:
                res.write({'state' : 'cancel'})
        
