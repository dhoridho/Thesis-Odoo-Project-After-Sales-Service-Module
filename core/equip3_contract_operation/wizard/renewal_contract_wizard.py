from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta

class RenewalContract(models.TransientModel):
    _name = 'renewal.contract.wizard'
    _description = 'Renewal Contract Wizard'
    
    agreement_id = fields.Many2one('agreement', string='Agreement', required=True)
    name = fields.Char(string='Title', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    @api.onchange('start_date', 'agreement_id')
    def _onchange_end_date(self):
        if self.start_date and self.agreement_id:
            if self.agreement_id.recurring_invoice_id.recurring_type == 'daily':
                end_date = self.start_date + relativedelta(days=self.agreement_id.recurring_invoice_id.day)
            elif self.agreement_id.recurring_invoice_id.recurring_type == 'monthly':
                end_date = self.start_date + relativedelta(months=self.agreement_id.recurring_invoice_id.month)
            elif self.agreement_id.recurring_invoice_id.recurring_type == 'yearly':
                end_date = self.start_date + relativedelta(years=self.agreement_id.recurring_invoice_id.year)
            
            self.end_date = end_date

    
    def create_new_contract(self):
        self.ensure_one()
        res = self.agreement_id.create_new_agreement()
        agreement = self.env[res["res_model"]].browse(res["res_id"])
        if agreement:
            product = []
            for line in self.env['agreement'].browse(self.agreement_id.id).line_ids:
                product.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'qty': line.qty,
                    'uom_id': line.uom_id.id,
                }))
            # expenses=[]
            # for line in self.env['agreement'].browse(self.agreement_id.id).expense_line_ids:
            #     expenses.append((0, 0, {
            #         'product_id': line.product_id.id,
            #         'name': line.name,
            #         'qty': line.qty,
            #         'uom_id': line.uom_id.id,
            #     }))
            agree = agreement.write(
                {
                    "name": self.name,
                    "description": self.name,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "line_ids": product,
                    # "expense_line_ids": expenses,
                    "last_contract": self.agreement_id.id,
                    "stage_id": self.env['agreement.stage'].search([('name', '=', 'Active')], limit=1).id,
                }
            )
            if agree:
                line = self.env['agreement.renewal.line']
                if self.agreement_id.agreement_renewal_code == False or self.agreement_id.agreement_renewal_code == 0:
                    code = self.env['ir.sequence'].next_by_code('renewal.contract.line')
                    self.agreement_id.write({'agreement_renewal_code': code})
                    agreement.write({'agreement_renewal_code': code})
                    line.create({
                        'agreement_id': self.agreement_id.id,
                        'desc': 'First Contract',
                        'agreement_renewal_code': code,
                    })
                    line.create({
                        'agreement_id': agreement.id,
                        'desc': 'Renewal from Contract [' + self.agreement_id.code + '] '+ self.agreement_id.name,
                        'agreement_renewal_code': code,
                    })
                    return res
                else:
                    code = self.agreement_id.agreement_renewal_code
                    agreement.write({'agreement_renewal_code': code})
                    line.create({
                        'agreement_id': agreement.id,
                        'desc': 'Renewal from Contract [' + self.agreement_id.code + '] '+ self.agreement_id.name,
                        'agreement_renewal_code': code,
                    }) 
                    return res