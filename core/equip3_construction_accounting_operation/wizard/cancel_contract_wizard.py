from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta


class CancelContractWizard(models.TransientModel):
    _name = 'cancel.contract.wizard'
    _description = 'Confirmation wizard for cancel a Contract'

    contract_id = fields.Many2one('variation.order.line', string='Contract')
    project_id = fields.Many2one(related='contract_id.project_id')
    sale_order_id = fields.Many2one(related='contract_id.name')
    progressive_claim_names = fields.Char(string='Progress Claim : ', compute='_compute_progressive_claim_names')
    warning = fields.Html(string='Warning')
    responsible = fields.Selection([('contractor', 'Contractor'), ('client', 'Client')], string='Responsible')
    reason = fields.Text(string='Reason', required=True)
    department_type = fields.Selection([
        ('department', 'Internal'),
        ('project', 'External'),
    ], string='Type of Project')
    sale_order_count = fields.Integer(string='Customer Contract', compute='_compute_integer')
    purchase_order_count = fields.Integer(string='Subcon Contract', compute='_compute_integer')
    cost_sheet_count = fields.Integer(string='Cost Sheet', compute='_compute_integer')
    job_order_count = fields.Integer(string='Job Order', compute='_compute_integer')
    job_order_subcon_count = fields.Integer(string='Job Subcon', compute='_compute_integer')
    claim_customer_count = fields.Integer(string='Claim Customer', compute='_compute_integer')
    claim_subcon_count = fields.Integer(string='Claim Subcon', compute='_compute_integer')
    invoice_count = fields.Integer(string='Invoices', compute='_compute_integer')
    bill_count = fields.Integer(string='Bills', compute='_compute_integer')
    payment_method = fields.Selection(related='contract_id.vo_payment_type')
    warning_2 = fields.Html(string='Warning 2')
 
    
    @api.depends('contract_id')
    def _compute_integer(self):
        for rec in self:
            if rec.contract_id.vo_payment_type =='join':
                parent = rec.sale_order_id.contract_parent
                
                # Contract Customer
                rec.sale_order_count = len(rec.sale_order_id)

                # Cost Sheet
                rec.cost_sheet_count = self.env['job.cost.sheet'].search_count([('project_id', '=', rec.project_id.id), ('state', 'not in', ['cancelled','reject','revised'])])
                
                # Claim Customer
                rec.claim_customer_count = self.env['progressive.claim'].search_count([('project_id', '=', rec.project_id.id), ('contract_parent', '=', parent.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')])
                
                # Other
                rec.purchase_order_count = 0
                rec.job_order_count = 0
                rec.job_order_subcon_count = 0
                rec.invoice_count = 0
                rec.claim_subcon_count = 0
                rec.bill_count = 0
                
            else:
                parent = rec.sale_order_id.contract_parent
                
                # Contract Customer
                rec.sale_order_count = self.env['sale.order.const'].search_count([('project_id', '=', rec.project_id.id), ('contract_parent', '=', rec.sale_order_id.id), ('state', '!=', 'cancelled')])

                # Cost Sheet
                rec.cost_sheet_count = self.env['job.cost.sheet'].search_count([('project_id', '=', rec.project_id.id), ('state', 'not in', ['cancelled','reject','revised'])])
                
                # Claim Customer
                rec.claim_customer_count = self.env['progressive.claim'].search_count([('project_id', '=', rec.project_id.id), ('contract_parent', '=', rec.sale_order_id.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')])
                
                claim_customer = self.env['progressive.claim'].search([('project_id', '=', rec.project_id.id), ('contract_parent', '=', rec.sale_order_id.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')])
                if len(claim_customer)>0:
                    for claim in claim_customer:
                        rec.invoice_count += self.env['account.move'].search_count([('claim_id','=',claim.id), ('state', '=', 'draft')])
                else:
                    rec.invoice_count = 0

                # Contract Subcon
                rec.purchase_order_count = self.env['purchase.order'].search_count([('project', '=', rec.project_id.id), ('is_subcontracting', '=', True), ('contract_customer', '=', rec.sale_order_id.id), ('state', '=', 'purchase')])
                
                # Claim & Bill Subcon
                purchase_order = self.env['purchase.order'].search([('project', '=', rec.project_id.id), ('is_subcontracting', '=', True), ('contract_customer', '=', rec.sale_order_id.id), ('state', '=', 'purchase')])
                claim_subcon = []
                i = 0
                for purchase in purchase_order:
                    if i == 0:
                        claim_subcon.append(self.env['progressive.claim'].search([('project_id', '=', rec.project_id.id), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')]))
                        i+=1
                    else:
                        claim_subcon[0] += self.env['progressive.claim'].search([('project_id', '=', rec.project_id.id), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')])

                if len(claim_subcon)>0:
                    rec.claim_subcon_count = len(claim_subcon[0])
                    for claim in claim_subcon[0]:
                        rec.bill_count += self.env['account.move'].search_count([('project_id', '=', rec.project_id.id), ('progressive_bill', '=', True), ('claim_id','=',claim.id), ('state', 'not in', ('posted','cancel'))])
                else:
                    rec.claim_subcon_count = 0
                    rec.bill_count = 0

                # Job Order Customer
                rec.job_order_count = self.env['project.task'].search_count([('project_id', '=', rec.project_id.id), ('sale_order', '=', rec.sale_order_id.id)])

                # Job Order Subcon
                if len(purchase_order)>0:
                    for purchase in purchase_order:
                        rec.job_order_subcon_count += self.env['project.task'].search_count([('project_id', '=', rec.project_id.id), ('sale_order', '=', rec.sale_order_id.id), ('purchase_subcon', '=', purchase.id)])
                else:
                    rec.job_order_subcon_count = 0
                    

    @api.depends('contract_id')
    def _compute_progressive_claim_names(self):
        sale_order_ids = self.env['sale.order.const'].search([('id', '=', self.contract_id.name.id), ('state', '=', 'sale')])
        progressive_claim_ids = self.env['progressive.claim'].search([('contract_parent', '=', self.contract_id.name.id)])
        invoice_bill_ids = list()

        temp_list = list()
        for record in progressive_claim_ids:
            temp_list.append(record.name)
        self.progressive_claim_names = ', '.join(temp_list)

        temp_warning ="""
        <h2>Are you sure you want to cancel this contract? If yes, these following documents will also be cancelled:</h2>
        <br/>
        """
        
        self.warning = temp_warning

        temp_warning_2 ="""
        <br/>
        <h2>These following documents will be updated: </h2>
        """
        
        self.warning_2 = temp_warning_2

    def confirm(self):
        sale_order_ids = self.env['sale.order.const'].search([('id', '=', self.sale_order_id.id), ('state', '=', 'sale')])
        contract_ids = self.env['contract.history'].search([('contract_history', '=', self.sale_order_id.id)])
        
        for contract in self.contract_id:
            contract.responsible = self.responsible
            contract.reason = self.reason
            contract.cancel_date = datetime.now()
        
        for sale_order in sale_order_ids:
            cost_sheet = self.env['job.cost.sheet'].search([])
            for rec in cost_sheet:
                if sale_order.id in rec.sale_order_ref.ids:
                    rec.sale_order_ref = [(3, sale_order.id)]
                    # rec.sudo()._onchange_sale_order_ref_2()

        for history in contract_ids:
             history.state = 'cancel'

        if self.contract_id.vo_payment_type == 'join':
            sale_order_ids = self.env['sale.order.const'].search([('id', '=', self.sale_order_id.id), ('state', '=', 'sale')])
            for sale_order in sale_order_ids:
                sale_order.state = 'cancel'
                sale_order.responsible = self.responsible
                sale_order.reason = self.reason
                
            # purchase_order = self.env['purchase.order'].search([('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('contract_customer', '=', self.contract_id.name.id), ('state', '=', 'purchase')])
            # claim_customer = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent', '=', self.contract_id.name.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')])
            # cost_sheet = self.env['job.cost.sheet'].search([('project_id', '=', self.project_id.id), ('state', '!=', 'cancelled'), ])
            # job_order = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sale_order', '=', self.sale_order_id.id)])

            # if len(purchase_order)>0:
            #     job_order_subcon = []
            #     claim_subcon = []
            #     i = 0
            #     for purchase in purchase_order:
            #         if i == 0:
            #             job_order_subcon.append(self.env['project.task'].search([('project_id', '=', self.project_id.id), ('purchase_subcon', '=', purchase.id)]))
            #             claim_subcon.append(self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')]))
            #         else:
            #             job_order_subcon[0] += self.env['project.task'].search([('project_id', '=', self.project_id.id), ('purchase_subcon', '=', purchase.id)])
            #             claim_subcon[0] += self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')])
            # else:
            #     job_order_subcon = []
            #     claim_subcon = []
            
            # invoice = []
            # j = 0
            # for claim in claim_customer:
            #     if j == 0:
            #         invoice.append(self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')]))
            #         j+=1
            #     else:
            #         invoice[0] += self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')])

            # if len(claim_subcon)>0:
            #     bill = []
            #     i = 0
            #     for claim in claim_subcon:
            #         if i == 0:
            #             bill.append(self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')]))
            #             i+=1
            #         else:
            #             bill[0] += self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')])
                    
            # else:
            #     bill = []

            # self.sale_order_id.write({
            #     'state': 'cancel',
            # })

            # for claim in claim_customer:
            #     claim.write({
            #         'state': 'cancel',
            #     })
            # if len(invoice)>0:
            #     for inv in invoice[0]:
            #         inv.write({
            #             'state': 'cancel',
            #         })

            # for order in job_order:
            #     order.write({
            #         'state': 'cancel',
            #     })
            
            # if len(purchase_order)>0:
            #     for purchase in purchase_order:
            #         purchase.write({
            #             'state': 'cancel',
            #         })
            #     if len(job_order_subcon)>0:
            #         for job in job_order_subcon[0]:
            #             job.write({
            #                 'state': 'cancel',
            #             })
            #     if len(claim_subcon)>0:
            #         for claim in claim_subcon[0]:
            #             claim.write({
            #                 'state': 'cancel',
            #             })
            #         if len(bill)>0:
            #             for bill in bill[0]:
            #                 bill.write({
            #                     'state': 'cancel',
            #                 })

        elif self.contract_id.vo_payment_type == 'split':
            # Contract Customer
            sale_order_ids = self.env['sale.order.const'].search([('project_id', '=', self.project_id.id), ('contract_parent', '=', self.sale_order_id.id), ('state', '=', 'sale')])
            for sale_order in sale_order_ids:
                sale_order.state = 'cancel'
                sale_order.responsible = self.responsible
                sale_order.reason = self.reason

            # Purchase Subcon, Claim Subcon, Bill Subcon
            purchase_main = self.env['purchase.order'].search([('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('sub_contracting', '=', 'main_contract'), ('contract_customer', '=', self.sale_order_id.id), ('state', '=', 'purchase')])
            if purchase_main:
                for main in purchase_main:
                    main.responsible = 'contractor'
                    main.reason = 'This contract customer has been cancelled'
            
            purchase_order = self.env['purchase.order'].search([('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('contract_customer', '=', self.sale_order_id.id), ('state', '=', 'purchase')])
            if len(purchase_order)>0:
                job_order_subcon = []
                claim_subcon = []
                i = 0
                for purchase in purchase_order:
                    if i == 0:
                        job_order_subcon.append(self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sale_order', '=', rec.sale_order_id.id),  ('purchase_subcon', '=', purchase.id)]))
                        claim_subcon.append(self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('progressive_bill', '=', True), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')]))
                    else:
                        job_order_subcon[0] += self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sale_order', '=', rec.sale_order_id.id), ('purchase_subcon', '=', purchase.id)])
                        claim_subcon[0] += self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('progressive_bill', '=', True), ('contract_parent_po', '=', purchase.id), ('state', '!=', 'cancel')])
            else:
                job_order_subcon = []
                claim_subcon = []

            if len(claim_subcon)>0:
                bill = []
                i = 0
                for claim in claim_subcon:
                    if i == 0:
                        bill.append(self.env['account.move'].search([('progressive_bill', '=', True), ('claim_id','=',claim.id), ('state', 'not in', ('posted','cancel'))]))
                        i+=1
                    else:
                        bill[0] += self.env['account.move'].search([('progressive_bill', '=', True), ('claim_id','=',claim.id), ('state', 'not in', ('posted','cancel'))])
                    
            else:
                bill = []
            
            if len(purchase_order)>0:
                for purchase in purchase_order:
                    purchase.write({
                        'state': 'cancel',
                    })
                if len(job_order_subcon)>0:
                    for job in job_order_subcon[0]:
                        job.write({
                            'state': 'cancel',
                        })
                if len(claim_subcon)>0:
                    for claim in claim_subcon[0]:
                        claim.write({
                            'state': 'cancel',
                        })
                    if len(bill)>0:
                        for bill in bill[0]:
                            bill.write({
                                'state': 'cancel',
                            })

            # Claim Customer & Invoice Customer
            progressive_claim_ids = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('progressive_bill', '=', False), ('contract_parent', '=', self.sale_order_id.id), ('state', '!=', 'cancel')])
            invoice = []
            j = 0
            for claim in progressive_claim_ids:
                if j == 0:
                    invoice.append(self.env['account.move'].search([('progressive_bill', '=', False), ('claim_id','=',claim.id), ('state', 'not in', ('posted','cancel'))]))
                    j+=1
                else:
                    invoice[0] += self.env['account.move'].search([('progressive_bill', '=', False), ('claim_id','=',claim.id), ('state', 'not in', ('posted','cancel'))])

            for claim in progressive_claim_ids:
                claim.write({
                    'state': 'cancel',
                })

            if len(invoice)>0:
                for inv in invoice[0]:
                    inv.write({
                        'state': 'cancel',
                    })
            
            # Job Order Customer
            job_order = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sale_order', '=', self.sale_order_id.id)])

            for order in job_order:
                order.write({
                    'state': 'cancel',
                })

            
            # joined_contract = self.env['sale.order.const'].search([('project_id', '=', self.project_id.id), ('contract_parent', '=', self.sale_order_id.id), ('vo_payment_type','=', 'join'), ('state', '=', 'sale')])

            # if len(joined_contract)>0:
            #     joined_contract_history_ids = self.env['contract.history'].search([('contract_history', '=', self.joined_contract.name.id)])

            #     for sale_order in joined_contract:
            #         sale_order.state = 'cancel'
            #         sale_order.responsible = self.responsible
            #         sale_order.reason = self.reason
            #         cost_sheet = self.env['job.cost.sheet'].search([])
            #         for rec in cost_sheet:
            #             if sale_order.id in rec.sale_order_ref.ids:
            #                 rec.sale_order_ref = [(3, sale_order.id)]
            #                 rec.sudo()._onchange_sale_order_ref_2()

    
            #     for history in joined_contract_history_ids:
            #         history.state = 'cancel'

            #     purchase_order = self.env['purchase.order'].search([('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('contract_customer', '=', self.joined_contract.id), ('state', '=', 'purchase')])
            #     claim_customer = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent', '=', self.joined_contract.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')])
            #     cost_sheet = self.env['job.cost.sheet'].search([('project_id', '=', self.project_id.id), ('state', '!=', 'cancelled'), ])
            #     job_order = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sale_order', '=', joined_contract.id)])

            #     if len(purchase_order)>0:
            #         job_order_subcon = []
            #         claim_subcon = []
            #         i = 0
            #         for purchase in purchase_order:
            #             if i == 0:
            #                 job_order_subcon.append(self.env['project.task'].search([('project_id', '=', self.project_id.id), ('purchase_subcon', '=', purchase.id)]))
            #                 claim_subcon.append(self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')]))
            #             else:
            #                 job_order_subcon[0] += self.env['project.task'].search([('project_id', '=', self.project_id.id), ('purchase_subcon', '=', purchase.id)])
            #                 claim_subcon[0] += self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent_po', '=', purchase.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')])
            #     else:
            #         job_order_subcon = []
            #         claim_subcon = []

            #     invoice = []
            #     j = 0
            #     for claim in claim_customer:
            #         if j == 0:
            #             invoice.append(self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')]))
            #             j+=1
            #         else:
            #             invoice[0] += self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')])

            #     if len(claim_subcon)>0:
            #         bill = []
            #         i = 0
            #         for claim in claim_subcon:
            #             if i == 0:
            #                 bill.append(self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')]))
            #                 i+=1
            #             else:
            #                 bill[0] += self.env['account.move'].search([('claim_id','=',claim.id), ('state', '=', 'draft')])
                        
            #     else:
            #         bill = []

            #     self.sale_order_id.write({
            #         'state': 'cancel',
            #     })

            #     for claim in claim_customer:
            #         claim.write({
            #             'state': 'cancel',
            #         })

            #     if len(invoice)>0:
            #         for inv in invoice[0]:
            #             inv.write({
            #                 'state': 'cancel',
            #             })

            #     for order in job_order:
            #         order.write({
            #             'state': 'cancel',
            #         })
                
            #     if len(purchase_order)>0:
            #         for purchase in purchase_order:
            #             purchase.write({
            #                 'state': 'cancel',
            #             })
            #         if len(job_order_subcon)>0:
            #             for job in job_order_subcon[0]:
            #                 job.write({
            #                     'state': 'cancel',
            #                 })
            #         if len(claim_subcon)>0:
            #             for claim in claim_subcon[0]:
            #                 claim.write({
            #                     'state': 'cancel',
            #                 })
            #             if len(bill)>0:
            #                 for bill in bill[0]:
            #                     bill.write({
            #                         'state': 'cancel',
            #                     })

    def action_sale_order(self):
        if self.contract_id.vo_payment_type == 'join':
            domain = [('project_id', '=', self.project_id.id), ('id', '=', self.sale_order_id.id), ('state', '=', 'sale')]
        else:
            domain = [('project_id', '=', self.project_id.id), ('contract_parent', '=', self.sale_order_id.id), ('state', '=', 'sale')]

        return {
            'name': ("Contract Customer"),
            'view_mode': 'tree',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': domain,
        }

    def cost_sheet(self):
        return {
            'name': ("Cost Sheet"),
            'view_mode': 'tree',
            'res_model': 'job.cost.sheet',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('state', 'not in', ['cancelled','reject','revised'])],
        }

    def progressive_claim_customer(self):
        parent = self.sale_order_id.contract_parent
        if self.contract_id.vo_payment_type == 'join':
            domain = [('project_id', '=', self.project_id.id), ('contract_parent', '=', parent.id), ('state', '=', 'sale')]
        else:
            domain = [('project_id', '=', self.project_id.id), ('contract_parent', '=', self.sale_order_id.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')]
       
        return {
            'name': ("Customer Claim"),
            'view_mode': 'tree',
            'res_model': 'progressive.claim',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': domain,
        }
        
    def purchase_subcon(self):
        return {
            'name': ("Contract Subcon"),
            'view_mode': 'tree',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('contract_customer', '=', self.sale_order_id.id), ('state', '=', 'purchase')],
        }

    def job_order(self):
        return {
            'name': ("Job Order"),
            'view_mode': 'tree',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('is_subcon', '=', False), ('sale_order', '=', self.sale_order_id.id), ('state', 'not in', ('complete','cancel'))],
        }

    def job_order_subcon(self):
        return {
            'name': ("Job Order Subcon"),
            'view_mode': 'tree',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('is_subcon', '=', True), ('sale_order', '=', self.sale_order_id.id), ('state', 'not in', ('complete','cancel'))],
        }

    def progressive_claim_subcon(self):
        return {
            'name': ("Subcon Claim"),
            'view_mode': 'tree',
            'res_model': 'progressive.claim',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('progressive_bill', '=', True), ('contract_parent_po.contract_customer', '=', self.sale_order_id.id), ('state', '!=', 'cancel')],
        }
    
    def progressive_invoice(self):
        claim = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('contract_parent', '=', self.sale_order_id.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')]) 
        return {
            'name': ("Progressive Invoice"),
            'view_mode': 'tree',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', self.project_id.id), ('claim_id', '=', claim.id), ('progressive_bill', '=', False),('state', 'not in', ('posted','cancel'))],
        }

    def progressive_bill(self):
        return {
            'name': ("Progressive Bill"),
            'view_mode': 'tree',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', self.project_id.id), ('claim_id.contract_parent_po.contract_customer', '=', self.sale_order_id.id), ('progressive_bill', '=', True),('state', 'not in', ('posted','cancel'))],
        }

