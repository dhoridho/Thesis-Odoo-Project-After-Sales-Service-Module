from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta


class CreateProgressiveInvoiceWiz(models.TransientModel):
    _name = 'progressive.invoice.wiz'
    _description = 'Create Progressive Invoice'

    approved_progress = fields.Float(string='Approved Progress')
    invoice_progress = fields.Float(string='Invoice Progress', digits=(2,2))
    invoice_for = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
        ], string='Invoice Type')
    method = fields.Selection([
        ('fix', 'Fixed'),
        ('per', 'Percentage')
        ], string='Method', default="per")
    progressive_claim_id = fields.Many2one('progressive.claim', string="Progressive Claim")
    approved_amount = fields.Float(string='Approved Amount', compute="_compute_approved_amount")
    currency_id = fields.Many2one(related='progressive_claim_id.currency_id', string="Currency")
    contract_amount = fields.Float(string='Contract Amount')
    down_payment = fields.Float(string="Down Payment")
    dp_amount = fields.Float(string="Amount")
    retention1 = fields.Float(string="Retention 1")
    retention2 = fields.Float(string="Retention 2")
    retention1_amount = fields.Float(string="Amount")
    retention2_amount = fields.Float(string="Amount")
    tax_id = fields.Many2many('account.tax', 'taxes1', string="Taxes")
    vat_tax = fields.Many2many('account.tax', 'vat_tax1', string="VAT Tax")
    income_tax = fields.Many2many('account.tax', 'income_tax1', string="Income Tax")
    gross_amount = fields.Float(string="Gross Amount", compute="_compute_amount")
    dp_deduction = fields.Float(string="DP Deduction", compute="_compute_amount")
    dp_deduction_temp = fields.Float(string="DP Deduction Temp", compute="_compute_amount")
    retention_deduction = fields.Float(string="Retention Deduction", compute="_compute_amount")
    retention_deduction_temp = fields.Float(string="Retention Deduction Temp", compute="_compute_amount")
    amount_deduction = fields.Float(string="Amount After Deduction", compute="_compute_amount")
    amount_untaxed = fields.Float(string="Amount Untaxed", compute="_compute_amount")
    tax_amount = fields.Float(string="Tax Amount", compute="_compute_amount")
    amount_invoice = fields.Float(string="Total Amount to Invoice", compute="_compute_amount")
    dp_progress = fields.Float(string="Down Payment", compute="_compute_amount", digits=(2,2))
    progress = fields.Float(string="Progress", compute="_compute_amount", digits=(2,2))
    last_progress = fields.Float('Last Invoice Progress', digits=(2,2))
    last_amount = fields.Float('Last Invoice Amount')
    progressive_bill = fields.Boolean('Progressive Bill', default=False)
    paid_invoice = fields.Monetary(string="Paid Invoice", compute='_compute_amount')
    milestone_id = fields.Many2one('account.milestone.term.const', string="Milestone")
    claim_type = fields.Selection([
        ('monthly', 'Monthly Claim'),
        ('milestone', 'Milestone and Contract Term')
        ], string='Claim Type', related='progressive_claim_id.claim_type')
    po_subcon_line_id = fields.Many2one(related='progressive_claim_id.po_subcon_line_id')

    @api.onchange('invoice_progress')
    def onchange_invoice_progress1(self):
        if self.invoice_for == 'progress':
            if self.progressive_bill == False:
                if self.method == 'fix':
                    if self.invoice_progress > self.approved_amount:
                        raise ValidationError(_("The inputted Invoice Amount exceeds the Actual and Approved Amount.\nPlease, re-input Invoice Progress."))
                    elif self.invoice_progress <= self.last_amount:
                        raise ValidationError(_("The inputted Invoice Amount must be greater than the Last Invoice Amount.\nPlease, re-input Invoice Progress."))
                elif self.method == 'per':
                    if self.invoice_progress > self.approved_progress:
                        raise ValidationError(_("The inputted Invoice Progress exceeds the Actual and Approved Progress.\nPlease, re-input Invoice Progress"))
                    elif self.invoice_progress <= self.last_progress:
                        raise ValidationError(_("The inputted Invoice Progress must be greater than the Last Invoice Progress.\nPlease, re-input Invoice Progress."))
            else:
                if self.method == 'fix':
                    if self.invoice_progress > self.approved_amount:
                        raise ValidationError(_("The inputted Bill Amount exceeds the Actual and Approved Amount.\nPlease, re-input Bill Progress."))
                    elif self.invoice_progress <= self.last_amount:
                        raise ValidationError(_("The inputted Bill Amount must be greater than the Last Bill Amount.\nPlease, re-input Bill Progress."))
                elif self.method == 'per':
                    if self.invoice_progress > self.approved_progress:
                        raise ValidationError(_("The inputted Bill Progress must be greater than the Last Bill Progress.\nPlease, re-input Bill Progress."))
                    elif self.invoice_progress <= self.last_progress:
                        raise ValidationError(_("The inputted Bill Progress must be greater than the Last Bill Progress.\nPlease, re-input Bill Progress."))
        

        if self.invoice_for == 'down_payment':
            if self.progressive_bill == False:
                if self.method == 'fix':
                    amount = self.invoice_progress + self.last_amount
                    if amount > self.dp_amount:
                        raise ValidationError(_("The inputted Invoice Amount exceeds Total Down Payment.\nPlease, re-input Invoice Progress."))
                elif self.method == 'per':
                    if self.invoice_progress <= self.last_progress:
                        raise ValidationError(_("The inputted Invoice Progress must be greater than the Last Down Payment Progress.\nPlease, re-input Invoice Progress."))
            else:
                if self.method == 'fix':
                    amount = self.invoice_progress + self.last_amount
                    if amount > self.dp_amount:
                        raise ValidationError(_("The inputted Bill Progress exceeds the Actual and Approved Progress.\nPlease, re-input Bill Progress."))
                elif self.method == 'per':
                    if self.invoice_progress <= self.last_progress:
                        raise ValidationError(_("The inputted Bill Progress must be greater than the Last Down Payment Progress.\nPlease, re-input Bill Progress."))

    @api.constrains('invoice_progress')
    def onchange_invoice_progress2(self):
        for res in self:
            if res.invoice_for == 'down_payment':
                if self.progressive_bill == False:
                    if self.method == 'per':
                        if self.invoice_progress > 100:
                            raise ValidationError(_("The inputted Invoice Progress exceeds 100%.\nPlease, re-input Invoice Progress."))
                else:
                    if self.method == 'per':
                        if self.invoice_progress > 100:
                            raise ValidationError(_("The inputted Bill Progress exceeds 100%.\nPlease, re-input Bill Progress."))

    # @api.onchange('invoice_progress')
    # def onchange_invoice_progress3(self):
    #     
    #         if self.invoice_for == 'progress':
    #             warning_mess = ''
    #             if self.progressive_bill == False:
    #                 if self.method == 'fix':
    #                     if self.invoice_progress > self.approved_amount:
    #                         warning_mess = {
    #                             'message': ('The inputted Invoice Amount exceeds the Actual and Approved Amount.\nif you want to continue, click Create Invoice.'),
    #                             'title': "Warning"
    #                         }
    #                 elif self.method == 'per':
    #                     if self.invoice_progress > self.approved_progress:
    #                         warning_mess = {
    #                             'message': ('The inputted Invoice Progress exceeds the Actual and Approved Progress.\nif you want to continue, click Create Invoice.'),
    #                             'title': "Warning"
    #                         }
    #             elif self.progressive_bill == True:
    #                 if self.method == 'fix':
    #                     if self.invoice_progress > self.approved_amount:
    #                         warning_mess = {
    #                             'message': ('The inputted Bill Amount exceeds the Actual and Approved Amount.\nif you want to continue, click Create Bill.'),
    #                             'title': "Warning"
    #                         }
    #                 elif self.method == 'per':
    #                     if self.invoice_progress > self.approved_progress:
    #                         warning_mess = {
    #                             'message': ('The inputted Bill Progress exceeds the Actual and Approved Progress.\nif you want to continue, click Create Bill.'),
    #                             'title': "Warning"
    #                         }
                    
    #             if warning_mess != '':
    #                 return {'warning': warning_mess, 'value':{}}

    #     else:
    #         if self.invoice_for == 'progress':
    #             if self.progressive_bill == False:
    #                 if self.method == 'fix':
    #                     if self.invoice_progress > self.approved_amount:
    #                         raise ValidationError(_("The inputted Invoice Amount exceeds the Actual and Approved Amount.\nPlease, re-input Invoice Progress."))
    #                 elif self.method == 'per':
    #                     if self.invoice_progress > self.approved_progress:
    #                         raise ValidationError(_("The inputted Invoice Progress exceeds the Actual and Approved Progress.\nPlease, re-input Invoice Progress."))
    #             else:
    #                 if self.method == 'fix':
    #                     if self.invoice_progress > self.approved_amount:
    #                         raise ValidationError(_("The inputted Bill Amount exceeds the Actual and Approved Amount.\nPlease, re-input Bill Progress."))
    #                 elif self.method == 'per':
    #                     if self.invoice_progress <= self.last_progress:
    #                         raise ValidationError(_("The inputted Bill Progress exceeds the Actual and Approved Progress.\nPlease, re-input Bill Progress."))
        
                
    @api.depends('contract_amount', 'approved_progress')
    def _compute_approved_amount(self):
        total = 0.0
        for res in self:
            total = res.contract_amount * (res.approved_progress / 100)
            res.approved_amount = total
        return total

    @api.depends('contract_amount', 'last_progress')
    def _compute_last_amount(self):
        tal = 0.0
        for res in self:
            tal = res.contract_amount * (res.last_progress / 100)
            res.last_amount = tal
        return tal

    @api.onchange('method')
    def onchange_method(self):
        if self.invoice_for == 'down_payment':
            for res in self.progressive_claim_id:
                if self.method == 'fix':
                    self.invoice_progress = res.dp_amount - self.last_amount
                elif self.method == 'per':
                    self.invoice_progress = 100
                    if self.milestone_id:
                        self.invoice_progress = self.milestone_id.claim_percentage
        elif self.invoice_for == 'progress':
            for res in self.progressive_claim_id:
                if self.method == 'fix':
                    self.invoice_progress = res.contract_amount * (res.approved_progress / 100)
                elif self.method == 'per':
                    self.invoice_progress = res.approved_progress
                    if self.milestone_id:
                        self.invoice_progress = self.milestone_id.claim_percentage
        elif self.invoice_for == 'retention1':
            for res in self.progressive_claim_id:
                self.invoice_progress = res.contract_amount * (res.retention1 / 100)
        elif self.invoice_for == 'retention2':
            for res in self.progressive_claim_id:
                self.invoice_progress = res.contract_amount * (res.retention2 / 100)


    # Calculation of amount invoice
    @api.depends('invoice_progress', 'contract_amount', 'dp_amount', 'retention1', 'progressive_claim_id',
                 'retention2', 'method', 'invoice_for', 'last_progress','tax_id')    
    def _compute_amount(self):
        for rec in self:
            invoice_for = rec.invoice_for
            method = rec.method
            invoice_progress = rec.invoice_progress
            contract_amount = rec.contract_amount
            dp_amount = rec.dp_amount
            retention1 = rec.retention1
            retention2 = rec.retention2
            last_progress = rec.last_progress
            last_amount = rec.last_amount
            tax_id = rec.tax_id
            claim = rec.progressive_claim_id
            
            def _compute_progress(invoice_for,dp_amount,last_amount,contract_amount,invoice_progress,method):
                vals = 0.0
                if invoice_for == 'down_payment':
                    if method == 'fix':
                        vals += ((invoice_progress + last_amount)/dp_amount) * 100
                    elif method == 'per':
                        vals += invoice_progress
                elif invoice_for == 'progress':
                    if method == 'fix':
                        vals += (invoice_progress/contract_amount) * 100
                    elif method == 'per':
                        vals += invoice_progress
                elif invoice_for == 'retention1':
                    vals += 100
                elif invoice_for == 'retention2':
                    vals += 100
                return vals

            def _compute_gross_amount(invoice_for,contract_amount,dp_amount,last_amount,invoice_progress,method):
                value = 0.0
                if invoice_for == 'down_payment':
                    if method == 'fix':
                        value += invoice_progress
                    elif method == 'per':
                        value += (dp_amount * (invoice_progress/100)) - last_amount
                elif invoice_for == 'progress':
                    if method == 'fix': 
                        value += invoice_progress
                    elif method == 'per':
                        value += contract_amount * (invoice_progress/100)
                elif invoice_for == 'retention1':
                    value += invoice_progress
                elif invoice_for == 'retention2':
                    value += invoice_progress
                return value

            def _compute_dp_deduction(invoice_for,contract_amount,invoice_progress,method,dp_amount):
                vals = 0.0
                if invoice_for != 'progress':
                    vals += 0.0
                elif invoice_for == 'progress':
                    if method == 'fix':
                        vals += ((invoice_progress/contract_amount) * dp_amount) 
                    elif method == 'per':
                        vals += (dp_amount * (invoice_progress/100))
                return vals

            def _compute_retention_deduction(invoice_for,gross_amount,retention1,retention2):
                cons = 0.0
                if invoice_for != 'progress':
                    cons += 0.0
                elif invoice_for == 'progress':
                    cons += (gross_amount * ((retention1/100) + (retention2/100)))
                return cons

            def _compute_amount_deduction(invoice_for,gross_amount,dp_deduction,retention_deduction):
                amt = 0.0
                if invoice_for != 'progress':
                    amt += gross_amount - (dp_deduction + retention_deduction)
                elif invoice_for == 'progress':
                    amt += gross_amount - (dp_deduction + retention_deduction)
                return amt

            def _compute_paid_invoice(invoice_for,claim):
                tot = 0.0
                cont = self.env['project.claim'].search([('claim_id', '=', claim.id), ('claim_for', '=', 'progress')])
                if invoice_for != 'progress':
                    tot += 0.0
                elif invoice_for == 'progress':
                    tot += sum(cont.mapped('amount_untaxed'))
                return tot
            
            def _compute_dp_deduction_temp(invoice_for,contract_amount,progress,last_progress,dp_amount):
                tot = 0.0
                if invoice_for != 'progress':
                    tot += 0.0
                elif invoice_for == 'progress':
                    tot += (contract_amount * ((progress - last_progress) / 100)) * ((dp_amount / contract_amount))
                return tot

            def _compute_retention_deduction_temp(invoice_for,contract_amount,progress,last_progress,retention1,retention2):
                tes = 0.0
                if invoice_for != 'progress':
                    tes += 0.0
                elif invoice_for == 'progress':
                    tes += (contract_amount * ((progress - last_progress) / 100)) * ((retention1 + retention2) / 100)
                return tes

            def _compute_amount_untaxed(invoice_for,gross_amount,amount_deduction,paid_invoice):
                cob = 0.0
                if invoice_for != 'progress':
                    cob += gross_amount
                elif invoice_for == 'progress':
                    cob += amount_deduction - paid_invoice
                return cob
            

            def _compute_amount_tax(tax_id,amount_untaxed):
                vals = 0.0
                for tax in tax_id:
                    vals += (tax.amount/100) * amount_untaxed
                return vals

            
            progress = _compute_progress(invoice_for,dp_amount,last_amount,contract_amount,invoice_progress,method)
            gross_amount = _compute_gross_amount(invoice_for,contract_amount,dp_amount,last_amount,invoice_progress,method)
            dp_deduction = _compute_dp_deduction(invoice_for,contract_amount,invoice_progress,method,dp_amount)
            retention_deduction =  _compute_retention_deduction(invoice_for,gross_amount,retention1,retention2)
            amount_deduction = _compute_amount_deduction(invoice_for,gross_amount,dp_deduction,retention_deduction)
            dp_deduction_temp = _compute_dp_deduction_temp(invoice_for,contract_amount,progress,last_progress,dp_amount)
            retention_deduction_temp = _compute_retention_deduction_temp(invoice_for,contract_amount,progress,last_progress,retention1,retention2)
            paid_invoice = _compute_paid_invoice(invoice_for,claim)
            amount_untaxed = _compute_amount_untaxed(invoice_for,gross_amount,amount_deduction,paid_invoice)
            tax_amount = _compute_amount_tax(tax_id,amount_untaxed) 


            rec.progress = progress
            rec.gross_amount = gross_amount
            rec.dp_deduction = dp_deduction
            rec.retention_deduction = retention_deduction
            rec.amount_deduction = amount_deduction
            rec.dp_deduction_temp = dp_deduction_temp
            rec.retention_deduction_temp = retention_deduction_temp
            rec.paid_invoice = paid_invoice
            rec.amount_untaxed = amount_untaxed
            rec.tax_amount = tax_amount
            rec.amount_invoice = amount_untaxed + tax_amount


    def create_invoice(self):
        if self.progressive_bill == False:
            if not self.progressive_claim_id.partner_id.property_account_receivable_id:
                raise ValidationError("Set account receivable for this customer first.")

            if self.invoice_for == 'down_payment':
                if not self.progressive_claim_id.project_id.down_payment_id:
                    raise ValidationError("Set account for down payment receivable first.")
            
            elif self.invoice_for == 'progress':
                if not self.progressive_claim_id.project_id.accrued_id:
                    raise ValidationError("Set account for claim request receivable first.")
            
            elif self.invoice_for == 'retention1':
                if not self.progressive_claim_id.project_id.retention_id:
                    raise ValidationError("Set account for retention receivable first.")
            
            elif self.invoice_for == 'retention2':
                if not self.progressive_claim_id.project_id.retention_id:
                    raise ValidationError("Set account for retention receivable first.")
        
        else:
            if not self.progressive_claim_id.vendor.property_account_payable_id:
                raise ValidationError("Set account payable for this vendor first.")

            if self.invoice_for == 'down_payment':
                if not self.progressive_claim_id.project_id.down_payment_account:
                    raise ValidationError("Set account for down payment payable first.")
            
            elif self.invoice_for == 'progress':
                if not self.progressive_claim_id.project_id.accrued_account:
                    raise ValidationError("Set account for claim request payable first.")
            
            elif self.invoice_for == 'retention1':
                if not self.progressive_claim_id.project_id.retention_account:
                    raise ValidationError("Set account for retention payable first.")
            
            elif self.invoice_for == 'retention2':
                if not self.progressive_claim_id.project_id.retention_account:
                    raise ValidationError("Set account for retention payable first.")
            
        def _get_context_invoice(progressive_claim_id,invoice_for,progress,gross_amount,dp_deduction,retention_deduction,amount_deduction,amount_untaxed,tax_amount,amount_invoice,tax_id,milestone_id):
            vals = {}
            vals['po_subcon_line_id'] = self.po_subcon_line_id.id
            vals['invoice_date'] = fields.Date.today()
            vals['claim_description'] = _get_claim_description(invoice_for,progress)
            vals['state'] = 'draft'
            vals['claim_id'] = progressive_claim_id.id
            vals['project_invoice'] = True
            vals['progressive_method'] = invoice_for
            vals['progress'] = progress
            vals['project_id'] = progressive_claim_id.project_id.id
            vals['company_id'] = progressive_claim_id.company_id.id
            vals['analytic_group_ids'] = progressive_claim_id.analytic_idz.ids
            vals['gross_amount'] = gross_amount
            vals['dp_deduction'] = dp_deduction
            vals['retention_deduction'] = retention_deduction
            vals['amount_deduction'] = amount_deduction
            vals['tax_amount'] = tax_amount
            vals['amount_invoice'] = amount_invoice
            vals['tax_id'] = tax_id
            vals['branch_id'] = progressive_claim_id.branch_id.id 

            if self.progressive_bill == False:
                vals['move_type'] = 'out_invoice'
                vals['contract_parent'] = progressive_claim_id.contract_parent.id
                vals['partner_id'] = progressive_claim_id.partner_id.id
            elif self.progressive_bill == True:
                vals['move_type'] = 'in_invoice'
                vals['contract_parent_po'] = progressive_claim_id.contract_parent_po.id
                vals['partner_id'] = progressive_claim_id.vendor.id
            
            if self.invoice_for == 'progress':
                vals['progressline'] = progress
            elif self.invoice_for != 'progress':
                vals['progressline'] = 0.0
            
            if self.claim_type == 'milestone':
                vals['milestone_id'] = milestone_id.id
            else:
                vals['milestone_id'] = False
            
            return vals
        
        def _get_claim_description(invoice_for,progress):
            value = ''
            if progressive_claim_id.claim_type == 'milestone':
                if invoice_for == 'down_payment':
                    value = f'Down Payment {progress}%'
                elif invoice_for == 'progress':
                    value = f'{self.milestone_id.name} {progress}%'
                elif invoice_for == 'retention1':
                    value = f'Retention 1 {progress}%'
                elif invoice_for == 'retention2':
                    value = f'Retention 2 {progress}%'
            else:
                if invoice_for == 'down_payment':
                    value = f'Down Payment {progress}%'
                elif invoice_for == 'progress':
                    value = f'Progressive {progress}%'
                elif invoice_for == 'retention1':
                    value = f'Retention 1 {progress}%'
                elif invoice_for == 'retention2':
                    value = f'Retention 2 {progress}%'
            return value
        
        def _get_invoice_line_ids(progressive_claim_id,invoice_for,progress,last_progress):
            # vals = False
            name = ''
            name1 = ''
            analytic_account_id = progressive_claim_id.project_id.analytic_account_id.id
            analytic_tag_ids = progressive_claim_id.project_id.analytic_idz.ids
            
            if self.progressive_bill == False:
                if invoice_for == 'down_payment':
                    name = 'Down Payment '
                    name1 += (' ' +str(progress) + '%')
                    account_use = progressive_claim_id.project_id.down_payment_id
                
                elif invoice_for == 'progress':
                    name = 'Progressive '
                    name1 += (' ' +str(progress) + '%')
                    account_use = progressive_claim_id.project_id.accrued_id
                
                elif invoice_for == 'retention1':
                    name = 'Retention 1 '
                    name1 += ' ' +str(100.0) + '%'
                    account_use = progressive_claim_id.project_id.retention_id
                
                elif invoice_for == 'retention2':
                    name = 'Retention 2 '
                    name1 += ' ' +str(100.0) + '%'
                    account_use = progressive_claim_id.project_id.retention_id
            
            else:
                if invoice_for == 'down_payment':
                    name = 'Down Payment '
                    name1 += (' ' +str(progress) + '%')
                    account_use = progressive_claim_id.project_id.down_payment_account
                
                elif invoice_for == 'progress':
                    name = 'Progressive '
                    name1 += (' ' +str(progress) + '%')
                    account_use = progressive_claim_id.project_id.accrued_account
                
                elif invoice_for == 'retention1':
                    name = 'Retention 1 '
                    name1 += ' ' +str(100.0) + '%'
                    account_use = progressive_claim_id.project_id.retention_account
                
                elif invoice_for == 'retention2':
                    name = 'Retention 2 '
                    name1 += ' ' +str(100.0) + '%'
                    account_use = progressive_claim_id.project_id.retention_account
                
            vals = {
                'name': name + name1,
                'analytic_tag_ids': analytic_tag_ids,
                'analytic_account_id': analytic_account_id,
                'quantity': 1,
                'progress': progress - last_progress,
                'gross_amount': self.gross_amount,
                'dp_deduction': self.dp_deduction,
                'retention_deduction': self.retention_deduction,
                'account_id': account_use.id,
                'tax_ids': [(6, 0, [v.id for v in progressive_claim_id.tax_id])], 
                # 'price_tax': self.tax_amount,
                'price_unit': self.amount_untaxed,
            }
            
            return vals
        
        def _create_inv(vals):
            move_obj = self.env['account.move']
            inv = move_obj.create(vals)
            invoice_line_ids = _get_invoice_line_ids(progressive_claim_id,invoice_for,progress,last_progress)
            if invoice_line_ids:
                inv.invoice_line_ids = [(0, 0 , invoice_line_ids)]
            return inv
        
        if self.tax_id:
            exist_tax = self.progressive_claim_id.taxes_ids.mapped('tax_id').ids
            for tax in self.tax_id:
                taxs = []
                if tax.amount >= 0:
                    if tax.id not in exist_tax:
                        taxs.append(tax.id)
                        self.progressive_claim_id.vat_tax = [(4, tax.id)]
                        self.progressive_claim_id.taxes_ids = [(0, 0, {'tax_id': tax.id})]
                taxs = []
                if tax.amount < 0:
                    if tax.id not in exist_tax:
                        taxs.append(tax.id)
                        self.progressive_claim_id.income_tax = [(4, tax.id)]
                        self.progressive_claim_id.taxes_ids = [(0, 0, {'tax_id': tax.id})]
        
        progressive_claim_id = self.progressive_claim_id
        invoice_for = self.invoice_for
        progress = self.progress
        last_progress = self.last_progress
        gross_amount = self.gross_amount
        dp_deduction = self.dp_deduction
        retention_deduction = self.retention_deduction
        amount_deduction = self.amount_deduction
        amount_untaxed = self.amount_untaxed
        tax_amount = self.tax_amount
        amount_invoice = self.amount_invoice
        tax_id = self.tax_id
        milestone_id = self.milestone_id
        
        vals = _get_context_invoice(
            progressive_claim_id, invoice_for, progress, gross_amount, dp_deduction, retention_deduction,
            amount_deduction, amount_untaxed, tax_amount, amount_invoice, tax_id, milestone_id)
        inv = _create_inv(vals)
        progressive_claim_id.create_claim_history()

        if self.progressive_claim_id.claim_type == "monthly" and self.progressive_claim_id.is_create_automatically == True:
            if self.invoice_for == 'down_payment' or self.invoice_for == 'retention1' or self.invoice_for == 'retention2':
                template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_invoice_created')
                if inv.move_type == "in_invoice":
                    action_id = self.env.ref('account.action_move_in_invoice_type')
                else:
                    action_id = self.env.ref('account.action_move_out_invoice_type')
                for user in self.progressive_claim_id.project_id.notification_claim:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url = base_url + '/web#id=' + str(inv.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.move'
                    ctx = {
                        'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                        'email_to' : user.partner_id.email,
                        'approver_name' : user.partner_id.name,
                        'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                        'url' : url,
                    }
                    if self.invoice_for == 'down_payment':
                        ctx['invoice_for'] = 'down payment'
                    elif self.invoice_for == 'retention1':
                        ctx['invoice_for'] = 'retention 1'
                    else:
                        ctx['invoice_for'] = 'retention 2'
                    if inv.move_type == "in_invoice":
                        ctx['type'] = 'bill'
                    else:
                        ctx['type'] = 'invoice'
                    template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)

        if self.progressive_claim_id.claim_type == False or (self.progressive_claim_id.claim_type == "monthly" and self.progressive_claim_id.is_create_automatically == False):
            if self.progressive_claim_id.claim_type == False:
                template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_invoice_created')
            else:
                template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_monthly_invoice_created')
            if inv.move_type == "in_invoice":
                action_id = self.env.ref('account.action_move_in_invoice_type')
            else:
                action_id = self.env.ref('account.action_move_out_invoice_type')
            for user in self.progressive_claim_id.project_id.notification_claim:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(inv.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.move'
                ctx = {
                    'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                    'email_to' : user.partner_id.email,
                    'approver_name' : user.partner_id.name,
                    'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                    'url' : url,
                }
                if self.invoice_for == 'down_payment':
                    ctx['invoice_for'] = 'down payment'
                    template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_invoice_created')
                elif self.invoice_for == 'progress':
                    ctx['invoice_for'] = 'progress'
                elif self.invoice_for == 'retention1':
                    ctx['invoice_for'] = 'retention 1'
                    template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_invoice_created')
                else:
                    ctx['invoice_for'] = 'retention 2'
                    template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_invoice_created')
                if inv.move_type == "in_invoice":
                    ctx['type'] = 'bill'
                else:
                    ctx['type'] = 'invoice'
                template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)

        if self.progressive_claim_id.claim_type == "milestone":
            invoice_template_id = self.env.ref('equip3_construction_accounting_operation.email_template_notification_milestone_invoice_created')
            if inv.move_type == "in_invoice":
                invoice_action_id = self.env.ref('account.action_move_in_invoice_type')
            else:
                invoice_action_id = self.env.ref('account.action_move_out_invoice_type')
                
            for user in self.progressive_claim_id.project_id.notification_claim:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(inv.id) + '&action='+ str(invoice_action_id.id) + '&view_type=form&model=account.move'
                ctx = {
                    'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                    'email_to' : user.partner_id.email,
                    'approver_name' : user.partner_id.name,
                    'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                    'url' : url,
                    'claim_percentage': self.milestone_id.claim_percentage,
                    'milestone_name': self.milestone_id.name,
                    'invoice_progress': self.invoice_progress
                }
                if self.invoice_for == 'down_payment':
                    ctx['invoice_for'] = 'down payment'
                elif self.invoice_for == 'progress':
                    ctx['invoice_for'] = 'progress'
                elif self.invoice_for == 'retention1':
                    ctx['invoice_for'] = 'retention 1'
                else:
                    ctx['invoice_for'] = 'retention 2'
                if inv.move_type == "in_invoice":
                    ctx['type'] = 'bill'
                else:
                    ctx['type'] = 'invoice'
                invoice_template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)

            if self.invoice_for == "down_payment" and self.invoice_progress < 100:
                dp_to_invoiced = False
                ct = 101
                for m in self.progressive_claim_id.milestone_term_ids:
                    if m.type_milestone == "down_payment" and m.claim_percentage > self.invoice_progress:
                        if m.claim_percentage < ct:
                            ct = m.claim_percentage
                            dp_to_invoiced = m

                if dp_to_invoiced != False:
                    template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_milestone_create_invoice')
                    if self.progressive_bill == False:
                        action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
                    else:
                        action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

                    for user in self.progressive_claim_id.project_id.notification_claim:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        url = base_url + '/web#id=' + str(self.progressive_claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
                        ctx = {
                            'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                            'email_to' : user.partner_id.email,
                            'approver_name' : user.partner_id.name,
                            'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                            'url' : url,
                            'next_milestone': dp_to_invoiced.name,
                            'invoice_for': "Down Payment"
                        }
                        template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)
                        
            if self.invoice_for == "progress" and self.invoice_progress == 100:
                retention1_to_invoiced = False
                ct = 101
                for m in self.progressive_claim_id.milestone_term_ids:
                    if m.type_milestone == "retention1":
                        if m.claim_percentage < ct:
                            ct = m.claim_percentage
                            retention1_to_invoiced = m

                if retention1_to_invoiced != False:
                    template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_milestone_create_invoice')
                    if self.progressive_bill == False:
                        action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
                    else:
                        action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

                    for user in self.progressive_claim_id.project_id.notification_claim:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        url = base_url + '/web#id=' + str(self.progressive_claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
                        ctx = {
                            'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                            'email_to' : user.partner_id.email,
                            'approver_name' : user.partner_id.name,
                            'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                            'url' : url,
                            'next_milestone': retention1_to_invoiced.name,
                            'invoice_for': "Retention 1"
                        }
                        template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)

            if self.invoice_for == "retention1":
                retention2_to_invoiced = False
                ct = 101
                for m in self.progressive_claim_id.milestone_term_ids:
                    if m.type_milestone == "retention2":
                        if m.claim_percentage < ct:
                            ct = m.claim_percentage
                            retention2_to_invoiced = m
                if retention2_to_invoiced != False:
                    template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_milestone_create_invoice')
                    if self.progressive_bill == False:
                        action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
                    else:
                        action_id = self.env.ref('equip3_construction_accounting_operation.progressive_bill_view_action')

                    for user in self.progressive_claim_id.project_id.notification_claim:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        url = base_url + '/web#id=' + str(self.progressive_claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
                        ctx = {
                            'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
                            'email_to' : user.partner_id.email,
                            'approver_name' : user.partner_id.name,
                            'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
                            'url' : url,
                            'next_milestone': retention2_to_invoiced.name,
                            'invoice_for': "Retention 2"
                        }
                        template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)


        action = {
            "name": "Invoice",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": inv.id,
            "view_mode": 'form',
            "target": "current",            
        }
        return action

        