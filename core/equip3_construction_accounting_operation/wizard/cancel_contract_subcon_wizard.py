from odoo import api, fields, models
from datetime import date, datetime, timedelta


class CancelContractSubcon(models.TransientModel):
    _name = 'cancel.contract.subcon'
    _description = 'Cancel Contract Subcon'

    contract_subcon = fields.Many2one('contract.subcon.const', string='Contract Subcon')
    purchase_order = fields.Many2one(related='contract_subcon.name', string='Purchase Order')
    vendor = fields.Many2one(related='contract_subcon.partner_id', string='Vendor')
    warning = fields.Html(string='Warning', compute='_compute_warning')
    warning_2 = fields.Html(string='Warning 2', compute='_compute_warning')
    responsible = fields.Selection([('contractor', 'Contractor'), ('vendor', 'Vendor')], string='Responsible')
    reason = fields.Text(string='Reason', required=True)
    
    cost_sheet_count = fields.Integer(string='Cost Sheet', compute='_compute_count')
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    job_subcon_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    sub_claim_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    bill_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')

    @api.depends('contract_subcon')
    def _compute_warning(self):

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

    @api.depends('contract_subcon')
    def _compute_count(self):
        cost_sheet_count = 0
        po_subcon_count = 0
        job_count = 0
        claim_subcon_count = 0
        bill_subcon_count = 0
        for res in self:
            cost_sheet_count = self.env['job.cost.sheet'].search_count([('project_id', '=', res.purchase_order.project.id), ('state', 'not in', ['cancelled','reject','revised'])])      
            
            po_subcon_count = self.env['purchase.order'].search_count([('project', '=', res.purchase_order.project.id), ('partner_id', '=', res.vendor.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])      
            
            po_subcon = self.env['purchase.order'].search([('project', '=', res.purchase_order.project.id), ('partner_id', '=', res.vendor.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])      
            if len(po_subcon) > 0:
                for job in po_subcon:
                    job_count += self.env['project.task'].search_count([('project_id', '=', res.purchase_order.project.id), ('purchase_subcon', '=', job.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))])
            
            claim_subcon_count = self.env['progressive.claim'].search_count([('vendor', '=', res.vendor.id), ('project_id', '=', res.purchase_order.project.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
            
            claim_subcon = self.env['progressive.claim'].search([('vendor', '=', res.vendor.id), ('project_id', '=', res.purchase_order.project.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
            if len(claim_subcon) > 0:
                for claim in claim_subcon:
                    bill_subcon_count += self.env['account.move'].search_count([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('claim_id','=',claim.id), ('partner_id', '=', res.vendor.id), ('state', 'not in', ('posted','cancel'))])
            
            self.cost_sheet_count = cost_sheet_count
            self.purchase_order_count = po_subcon_count
            self.job_subcon_count = job_count
            self.sub_claim_count = claim_subcon_count
            self.bill_count = bill_subcon_count

    def confirm(self):
        for contract in self.contract_subcon:
            contract.responsible = self.responsible
            contract.reason = self.reason
            contract.cancel_date = datetime.now()

        for variation in self.contract_subcon.variation_subcon_ids:
            variation.name.write({'state': 'cancel'})

        for purchase in self.purchase_order:
            purchase.state = 'cancel'
            purchase.responsible = self.responsible
            purchase.reason = self.reason

        po_subcon = self.env['purchase.order'].search([('project', '=', self.purchase_order.project.id), ('partner_id', '=', self.vendor.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])      
        if len(po_subcon) > 0:
            for job in po_subcon:
                job_subcon = self.env['project.task'].search([('project_id', '=', self.purchase_order.project.id), ('purchase_subcon', '=', job.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))])
                if len(job_subcon) > 0:
                    for task in job_subcon:
                        task.state = 'cancel'

        claim_subcon = self.env['progressive.claim'].search([('vendor', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
        if len(claim_subcon) > 0:
            for claim in claim_subcon:
                claim.state = 'cancel'

                bill_subcon = self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('claim_id','=',claim.id), ('partner_id', '=', self.vendor.id), ('state', 'not in', ('posted','cancel'))])
                if len(bill_subcon) > 0:
                    for bill in bill_subcon:
                        bill.state = 'cancel'

    def purchase_subcon(self):
        return {
            'name': ("Contract Subcon"),
            'view_mode': 'tree',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('partner_id', '=', self.vendor.id), ('project', '=', self.purchase_order.project.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')],
        }
    
    def progressive_claim_subcon(self):
        return {
            'name': ("Subcon Claim"),
            'view_mode': 'tree',
            'res_model': 'progressive.claim',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('vendor', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')],
        }
    
    def progressive_bill(self):
        return {
            'name': ("Progressive Bill"),
            'view_mode': 'tree',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('partner_id', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('progressive_bill', '=', True),('state', 'not in', ('posted','cancel'))],
        }

    def job_order_subcon(self):
        return {
            'name': ("Job Order Subcon"),
            'view_mode': 'tree',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.purchase_order.project.id), ('sub_contractor', '=', self.vendor.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))],
        }
    
    def cost_sheet(self):
        return {
            'name': ("Cost Sheet"),
            'view_mode': 'tree',
            'res_model': 'job.cost.sheet',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.purchase_order.project.id), ('state', 'not in', ['cancelled','reject','revised'])],
        }
    
class CancelContractSubconVaritionOrder(models.TransientModel):
    _name = 'cancel.contract.subcon.variation.order'
    _description = 'Cancel Contract Subcon Variation Order'

    contract_subcon = fields.Many2one('variation.subcon.line', string='Contract Subcon')
    purchase_order = fields.Many2one(related='contract_subcon.name', string='Purchase Order')
    vendor = fields.Many2one(related='contract_subcon.partner_id', string='Vendor')
    warning = fields.Html(string='Warning', compute='_compute_warning')
    warning_2 = fields.Html(string='Warning 2', compute='_compute_warning')
    responsible = fields.Selection([('contractor', 'Contractor'), ('vendor', 'Vendor')], string='Responsible')
    reason = fields.Text(string='Reason', required=True)
    
    cost_sheet_count = fields.Integer(string='Cost Sheet', compute='_compute_count')
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    job_subcon_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    sub_claim_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    bill_count = fields.Integer(string='Purchase Order Count', compute='_compute_count')
    vo_payment_type = fields.Selection(related='contract_subcon.vo_payment_type')

    @api.depends('contract_subcon')
    def _compute_warning(self):

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
    
    @api.depends('contract_subcon')
    def _compute_count(self):
        cost_sheet_count = 0
        po_subcon_count = 0
        job_count = 0
        claim_subcon_count = 0
        bill_subcon_count = 0
        for res in self:
            cost_sheet_count = self.env['job.cost.sheet'].search_count([('project_id', '=', res.purchase_order.project.id), ('state', 'not in', ['cancelled','reject','revised'])])      
            
            po_subcon_count = self.env['purchase.order'].search_count([('project', '=', res.purchase_order.project.id), ('partner_id', '=', res.vendor.id), ('sub_contracting', '=', 'addendum'), ('contract_parent_po', '=', res.purchase_order.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])      
            
            po_subcon = self.env['purchase.order'].search([('project', '=', res.purchase_order.project.id), ('partner_id', '=', res.vendor.id), ('sub_contracting', '=', 'addendum'), ('contract_parent_po', '=', res.purchase_order.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])      
            if len(po_subcon) > 0:
                for job in po_subcon:
                    job_count += self.env['project.task'].search_count([('project_id', '=', res.purchase_order.project.id), ('purchase_subcon', '=', job.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))])
            
            join_po = res.purchase_order.contract_parent_po
            if res.vo_payment_type == 'split_payment':
                claim_subcon_count = self.env['progressive.claim'].search_count([('vendor', '=', res.vendor.id), ('project_id', '=', res.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', res.purchase_order.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
                claim_subcon = self.env['progressive.claim'].search([('vendor', '=', res.vendor.id), ('project_id', '=', res.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', res.purchase_order.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
            else:
                claim_subcon_count = self.env['progressive.claim'].search_count([('vendor', '=', res.vendor.id), ('project_id', '=', res.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', join_po.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
                claim_subcon = self.env['progressive.claim'].search([('vendor', '=', res.vendor.id), ('project_id', '=', res.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', join_po.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])

            if len(claim_subcon) > 0:
                for claim in claim_subcon:
                    bill_subcon_count += self.env['account.move'].search_count([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('claim_id','=',claim.id), ('partner_id', '=', res.vendor.id), ('state', 'not in', ('posted','cancel'))])
            
            self.cost_sheet_count = cost_sheet_count
            self.purchase_order_count = po_subcon_count
            self.job_subcon_count = job_count
            self.sub_claim_count = claim_subcon_count
            self.bill_count = bill_subcon_count

    def confirm(self):
        for contract in self.contract_subcon:
            contract.responsible = self.responsible
            contract.reason = self.reason
            contract.cancel_date = datetime.now()

        for purchase in self.purchase_order:
            purchase.state = 'cancel'
            purchase.responsible = self.responsible
            purchase.reason = self.reason

        po_subcon = self.env['purchase.order'].search([('project', '=', self.purchase_order.project.id), ('partner_id', '=', self.vendor.id), ('sub_contracting', '=', 'addendum'), ('contract_parent_po', '=', self.purchase_order.id), ('id', '!=', self.purchase_order.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])      
        if len(po_subcon) > 0:
            for purc in po_subcon:
                purc.state = 'cancel'
                
            for job in po_subcon:
                job_subcon = self.env['project.task'].search([('project_id', '=', self.purchase_order.project.id), ('purchase_subcon', '=', job.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))])
                if len(job_subcon) > 0:
                    for task in job_subcon:
                        task.state = 'cancel'

        join_po = self.purchase_order.contract_parent_po
        if self.vo_payment_type == 'split_payment':
            claim_subcon = self.env['progressive.claim'].search([('vendor', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', self.purchase_order.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])    
        else:
            claim_subcon = self.env['progressive.claim'].search([('vendor', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', join_po.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')])
            
        if len(claim_subcon) > 0:
            for claim in claim_subcon:
                claim.state = 'cancel'

                bill_subcon += self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('claim_id','=',claim.id), ('partner_id', '=', self.vendor.id), ('state', 'not in', ('posted','cancel'))])
                if len(bill_subcon) > 0:
                    for bill in bill_subcon:
                        bill.state = 'cancel'
        
    def purchase_subcon(self):
        return {
            'name': ("Contract Subcon"),
            'view_mode': 'tree',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project', '=', self.purchase_order.project.id), ('partner_id', '=', self.vendor.id), ('sub_contracting', '=', 'addendum'), ('contract_parent_po', '=', self.purchase_order.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')],
        }
    
    def progressive_claim_subcon(self):
        join_po = self.purchase_order.contract_parent_po
        if self.vo_payment_type == 'split_payment':
            domain = [('vendor', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', self.purchase_order.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')]
        else:
            domain = [('vendor', '=', self.vendor.id), ('project_id', '=', self.purchase_order.project.id), ('contract_parent_po.contract_parent_po', '=', join_po.id), ('progressive_bill', '=', True), ('state', '!=', 'cancel')]
        
        return {
            'name': ("Subcon Claim"),
            'view_mode': 'tree',
            'res_model': 'progressive.claim',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': domain,
        }
    
    def progressive_bill(self):
        join_po = self.purchase_order.contract_parent_po
        if self.vo_payment_type == 'split_payment':
            domain = [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('claim_id.contract_parent_po.contract_parent_po', '=', self.purchase_order.id), ('partner_id', '=', self.vendor.id), ('state', 'not in', ('posted','cancel'))]    
        else:
            domain = [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('claim_id.contract_parent_po.contract_parent_po', '=', join_po.id), ('partner_id', '=', self.vendor.id), ('state', 'not in', ('posted','cancel'))]    
        
        return {
            'name': ("Progressive Bill"),
            'view_mode': 'tree',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': domain,
        }

    def job_order_subcon(self):
        return {
            'name': ("Job Order Subcon"),
            'view_mode': 'tree',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.purchase_order.project.id), ('purchase_subcon', '=', self.purchase_order.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))],
        }
    
    def cost_sheet(self):
        return {
            'name': ("Cost Sheet"),
            'view_mode': 'tree',
            'res_model': 'job.cost.sheet',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.purchase_order.project.id), ('state', 'not in', ['cancelled','reject','revised'])],
        }