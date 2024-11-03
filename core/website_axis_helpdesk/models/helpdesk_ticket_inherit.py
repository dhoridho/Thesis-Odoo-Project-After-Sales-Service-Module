# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _
import datetime

TICKET_PRIORITY = [
    ('0', 'All'),
    ('1', 'Low priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
    ('4', 'High'),
]

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.model
    def get_value(self):
        # cr = self._cr
        #
        # query = """
        #      SELECT cl.partner_id AS partner_name,count(*),rs.name AS partner_name
        #        FROM sale_order cl INNER JOIN res_partner rs ON (cl.partner_id = rs.id)
        #        group by cl.partner_id,rs.name
        #        order by cl.partner_id
        #
        #    """
        #
        # cr.execute(query)
        # payroll_data = cr.dictfetchall()
        # payroll_label = []
        # payroll_dataset = []
        # data_set = {}
        # for data in payroll_data:
        #     payroll_label.append(data['partner_name'])
        #     payroll_dataset.append(data['count'])
        #
        # data_set.update({"payroll_dataset": payroll_dataset})
        # data_set.update({"payroll_label": payroll_label})
        data_set = {'name': 'test name'}
        return data_set

    number = fields.Char('Sequence', readonly=True)
    timesheet_ids = fields.One2many('account.analytic.line','ticket_id','Timesheet')
    move_line_ids = fields.One2many('account.move.line', 'ticket_id', 'Account')
    project_project_id= fields.Many2one('project.project',string="Project")
    is_task = fields.Boolean()
    is_invoice = fields.Boolean()
    is_task_button =fields.Boolean()
    is_invoice_button =fields.Boolean()
    invoice_payment_term_id = fields.Many2one('account.payment.term',string='Payment Terms')
    journal_id = fields.Many2one('account.journal',string='Journal')   
    close_ticket = fields.Boolean()
    ticket_invoice_ids = fields.One2many('helpdesk.ticket.invoice', 'ticket_id', 'Ticket Invoice')
    partner_id = fields.Many2one('res.partner')
    is_invoice = fields.Boolean('Is Invoice', readonly=True)
    invoice_number= fields.Char(string="Invoice Number")
    is_ticket_closed =fields.Boolean(string='Is Ticket Closed')
    close_ticket_date = fields.Datetime(string='Close Ticket')
    comment= fields.Text(string='Comment')
    priority_new = fields.Selection(TICKET_PRIORITY, string='Customer Rating', default='0')
    account_detail = fields.Many2one('account.move',string='Account',track_visibility='onchange')
    account_total_data = fields.Float(string='Invoice Amount')

    
    def create_task(self):
        self.is_task= True
        task_id = self.env['project.task'].create({
                'name': self.name,
                'project_id': self.project_project_id.id,
                'partner_id' : self.partner_id.id,
                'description': self.description,
                })

    def task_action(self):
        self.is_task_button = True
        search_record = self.env['project.task'].search([('name','=',self.name),('description','=',self.description),('project_id','=',self.project_project_id.id)])
        if search_record:
            return {
                'name': _('Create Task'),
                'view_mode': 'form',
                'res_model': 'project.task',
                'res_id': search_record.id,
                'type': 'ir.actions.act_window',
                }





    def create_invoice(self):
        self.is_invoice = True
        if self.ticket_invoice_ids:
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.partner_id.id,
                'date': datetime.datetime.now(),
                'invoice_date': datetime.datetime.now(),

            })
           

            for product in self.ticket_invoice_ids:
                move.write({

                    'invoice_line_ids': [
                        (0, 0, {
                            'product_id': product.product_id,
                            'product_uom_id': False,
                            'quantity':  product.quantity,
                            'price_unit':product.product_id.list_price,
                            'price_subtotal': product.price_unit,
                            'tax_ids': product.product_id.taxes_id,
                        }),
                    ]
                })
               
            move.action_post()

            self.write({
                'is_invoice': True,
                'invoice_number': move.id,

            })
         

    def invoice_action(self):
        self.is_invoice_button = True
      
        search_invoice = self.env['account.move'].search([('partner_id','=',self.partner_id.id),
            ('id','=',self.invoice_number)])
      
        self.account_detail = search_invoice.id
        self.account_total_data = search_invoice.amount_residual
        
      
        return {
                'name': _('Create Invoice'),
                'view_mode': 'form',
                'res_model': 'account.move',
                'res_id': search_invoice.id,
                'type': 'ir.actions.act_window',
                }
    
class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    ticket_id = fields.Many2one('helpdesk.ticket','Ticket')

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ticket_id = fields.Many2one('helpdesk.ticket', 'Ticket')
    product_id_new = fields.Many2one('product.product',string="Product")
   

class HelpdeskTicketInvoice(models.Model):
    _name = 'helpdesk.ticket.invoice'
    _description = "Helpdesk Ticket Invoice"

    product_id = fields.Many2one('product.product', 'Product',required=True)
    name = fields.Char(related='product_id.name',string='Lable',required=True)
    tax = fields.Char(string='Tax')
    quantity = fields.Float('Quantity')
    price_unit = fields.Float(compute='_compute_abcd',string='Price',store=True)
    ticket_id = fields.Many2one('helpdesk.ticket', 'First')

    @api.depends('quantity')
    def _compute_abcd(self):
        for record in self:
            search = record.env['product.product'].sudo().search([('name','=',record.product_id.name)])
            for rec in search:
                record.price_unit = record.quantity * rec.list_price

    @api.onchange('product_id')
    def _onchange_tax(self):
        for record in self:
            search = record.env['product.product'].sudo().search([('name','=',record.product_id.name)])
            for rec in search:
                record.tax =search.taxes_id.name
