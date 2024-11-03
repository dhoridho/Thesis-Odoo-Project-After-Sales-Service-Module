from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta


class CancelProjectWizard(models.TransientModel):
    _name = 'cancel.project.wizard'
    _description = 'Confirmation wizard for cancel a project'

    project_id = fields.Many2one('project.project', string='project')
    project_name = fields.Char(string='Project : ', related='project_id.name')
    progressive_claim_names = fields.Char(string='Progress Claim : ', compute='_compute_progressive_claim_names')
    warning = fields.Html(string='Warning')
    responsible = fields.Selection([('contractor', 'Contractor'), ('client', 'Client')], string='Responsible')
    reason = fields.Text(string='Reason', required=True)
    department_type = fields.Selection([
        ('department', 'Internal'),
        ('project', 'External'),
    ], string='Type of Project')
    sale_order_count  = fields.Integer(string='Customer Contract', compute='_compute_integer')
    purchase_order_count = fields.Integer(string='Subcon Contract', compute='_compute_integer')
    cost_sheet_count = fields.Integer(string='Cost Sheet', compute='_compute_integer')
    budget_count = fields.Integer(string='Project Budget', compute='_compute_integer')
    job_order_count = fields.Integer(string='Job Order', compute='_compute_integer')
    job_subcon_count = fields.Integer(string='Job Order Subcon', compute='_compute_integer')
    issue_count = fields.Integer(string='Project issue', compute='_compute_integer')
    claim_customer_count = fields.Integer(string='Claim Customer', compute='_compute_integer')
    claim_vendor_count = fields.Integer(string='Claim Vendor', compute='_compute_integer')
    claim_invoice_count = fields.Integer(string='Progressive Invoice', compute='_compute_integer')
    claim_bill_count = fields.Integer(string='Progressive Bill', compute='_compute_integer')

    @api.depends('project_id')
    def _compute_integer(self):
        for rec in self:
            rec.sale_order_count = self.env['sale.order.const'].search_count([('project_id', '=', rec.project_id.id), ('state', '=', 'sale')])
            rec.purchase_order_count = self.env['purchase.order'].search_count([('project', '=', rec.project_id.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])
            rec.cost_sheet_count = self.env['job.cost.sheet'].search_count([('project_id', '=', rec.project_id.id), ('state', 'not in', ['cancelled','reject','revised'])])
            rec.budget_count = self.env['project.budget'].search_count([('project_id', '=', rec.project_id.id), ('state', '!=', 'cancelled')])
            rec.job_order_count = self.env['project.task'].search_count([('project_id', '=', rec.project_id.id), ('is_subcon', '=', False), ('state', 'not in', ('complete','cancel'))])
            rec.job_subcon_count = self.env['project.task'].search_count([('project_id', '=', rec.project_id.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))])
            rec.issue_count = self.env['project.issue'].search_count([('project_id', '=', rec.project_id.id), ('state', '!=', 'cancelled')])
            rec.claim_customer_count = self.env['progressive.claim'].search_count([('project_id', '=', rec.project_id.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')])
            rec.claim_vendor_count = self.env['progressive.claim'].search_count([('project_id', '=', rec.project_id.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')])
            rec.claim_invoice_count = self.env['account.move'].search_count([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', rec.project_id.id), ('progressive_bill', '=', False),('state', 'not in', ('posted','cancel'))])
            rec.claim_bill_count = self.env['account.move'].search_count([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', rec.project_id.id), ('progressive_bill', '=', True),('state', 'not in', ('posted','cancel'))])


    def sale_order(self):
        return {
            'name': ("Contract Customer"),
            'view_mode': 'tree',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('state', '=', 'sale')],
        }
    
    def purchase_subcon(self):
        return {
            'name': ("Contract Subcon"),
            'view_mode': 'tree',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')],
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

    def project_budget(self):
        return {
            'name': ("Project Budget"),
            'view_mode': 'tree',
            'res_model': 'project.budget',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('state', '!=', 'cancelled')],
        }

    def job_order(self):
        return {
            'name': ("Job Order"),
            'view_mode': 'tree',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('is_subcon', '=', False), ('state', 'not in', ('complete','cancel'))],
        }

    def job_order_subcon(self):
        return {
            'name': ("Job Order Subcon"),
            'view_mode': 'tree',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('is_subcon', '=', True), ('state', 'not in', ('complete','cancel'))],
        }

    def project_issue(self):
        return {
            'name': ("Project Issue"),
            'view_mode': 'tree',
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('state', '!=', 'cancelled')],
        }
        
    
    def progressive_claim_customer(self):
        return {
            'name': ("Customer Claim"),
            'view_mode': 'tree',
            'res_model': 'progressive.claim',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('progressive_bill', '=', False),('state', '!=', 'cancel')],
        }

    def progressive_claim_subcon(self):
        return {
            'name': ("Subcon Claim"),
            'view_mode': 'tree',
            'res_model': 'progressive.claim',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_id', '=', self.project_id.id), ('progressive_bill', '=', True),('state', '!=', 'cancel')],
        }
    
    def progressive_invoice(self):
        return {
            'name': ("Progressive Invoice"),
            'view_mode': 'tree',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', self.project_id.id), ('progressive_bill', '=', False),('state', 'not in', ('posted','cancel'))],
        }

    def progressive_bill(self):
        return {
            'name': ("Progressive Bill"),
            'view_mode': 'tree',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'domain': [('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', self.project_id.id), ('progressive_bill', '=', True),('state', 'not in', ('posted','cancel'))],
        }
    
    
    @api.depends('project_id')
    def _compute_progressive_claim_names(self):
        temp_warning = '''
        <h2>Are you sure you want to cancel this project? If yes, these following documents will also be cancelled:</h2>
        <br/>
        '''
        self.progressive_claim_names = ''
        self.warning = temp_warning
    

    def confirm(self):
        sale_order_ids = self.env['sale.order.const'].search([('project_id', '=', self.project_id.id), ('state', '=', 'sale')])
        purchase_order_ids = self.env['purchase.order'].search([('project', '=', self.project_id.id), ('is_subcontracting', '=', True), ('state', '=', 'purchase')])
        cost_sheet_ids = self.env['job.cost.sheet'].search([('project_id','=', self.project_id.id), ('state', 'not in', ['cancelled','reject','revised'])],limit=1)
        contract_ids = self.env['contract.history'].search([('job_sheet_id', '=', cost_sheet_ids.id), ('state', '!=', 'cancel')])
        budget_ids = self.env['project.budget'].search([('project_id', '=', self.project_id.id), ('state', '!=', 'cancelled')])
        job_order_ids = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('state', 'not in', ('complete','cancel'))])
        issue_ids = self.env['project.issue'].search([('project_id', '=', self.project_id.id), ('state', '!=', 'cancelled')])
        progressive_claim_ids = self.env['progressive.claim'].search([('project_id', '=', self.project_id.id), ('state', '!=', 'cancel')])
        invoice_bill_ids = self.env['account.move'].search([('project_invoice', '=', True), ('penalty_invoice', '=', False), ('project_id', '=', self.project_id.id), ('state', 'not in', ('posted','cancel'))])
        filtered_proj_budget_period = self.env['project.budget.period'].search([('project','=', self.project_id.id)])
        
        for project in self.project_id:
            project.primary_states = 'cancelled'
            project.responsible = self.responsible
            project.reason = self.reason
            project.cancel_date = datetime.now()

        for sale_order in sale_order_ids:
            sale_order.state = 'cancel'
            sale_order.responsible = self.responsible
            sale_order.reason = self.reason

        for purchase_order in purchase_order_ids:
            purchase_order.state = 'cancel'
            if purchase_order.sub_contracting == 'main_contract':
                purchase_order.responsible = 'contractor'
                purchase_order.reason = 'This project has been cancelled'

        for sheet in cost_sheet_ids:
            sheet.state = 'cancelled'

        for cont in contract_ids:
            cont.state = 'cancel'

        for bud in budget_ids:
            bud.state = 'cancelled'    

        for job in job_order_ids:
            job.state = 'cancel'

        for iss in issue_ids:
            iss.state = 'cancelled'
            iss.issue_stage_id = 4 
        
        for progressive in progressive_claim_ids:
            progressive.state = 'cancel'
        
        for inv in invoice_bill_ids:
            inv.state = 'cancel'

        if filtered_proj_budget_period:
            for rec in filtered_proj_budget_period:       
                rec.sudo().action_closed()

        

        
        
        
        
        

    

    
        

        
        


