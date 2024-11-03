# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2021-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################
from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import ValidationError

class ProjectIssue(models.Model):
    _name = 'project.issue'
    _description = "Project Issue"

    name = fields.Char(string = 'Name')
    issue_type_id = fields.Many2one('issue.type', string = 'Type Of Issue')
    project_id = fields.Many2one('project.project', string = 'Project')
    job_order_id = fields.Many2one('project.task', string = 'Job Order')
    job_order_ids = fields.Many2many('project.task', string = 'Job Orders')
    supplier_id = fields.Many2one('res.partner', string = 'Supplier')
    user_id = fields.Many2one('res.users', string = 'Assigned To')
    description = fields.Text(string = 'Description')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
    amount_total = fields.Monetary(string='Total', readonly=True, compute = '_amount_total')

    issue_line_ids = fields.One2many('project.issue.line','isuue_invoice_id', string = 'Issue Invoices')
    invoice_count = fields.Integer(string = 'Bills', compute = 'compute_invoice_count')

    @api.depends('issue_line_ids.amount_total')
    def _amount_total(self):
        total = 0
        for issue in self.issue_line_ids:
            if issue:
                total += issue.amount_total
        self.amount_total = total

    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id:
            job_order_list = []
            job_order_obj = self.env['project.task'].search([('project_id','=',self.project_id.id)])
            if job_order_obj:
                for job_order in job_order_obj:
                    if job_order:
                        job_order_list.append(job_order)
                if job_order_list:
                    self.job_order_ids = [(6,0,[v.id for v in job_order_list])]

    def compute_invoice_count(self):
        account_invoice_obj = self.env['account.move']
        for issue in self:
            issue.invoice_count = account_invoice_obj.search_count([('project_issue_id', '=', issue.id)])

    def action_view_invoice(self):
        return {
                'name': _('Invoice'),
                'domain': [('project_issue_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                #'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (self.env.ref('account.view_move_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def create_bill(self):
        if self.issue_line_ids:
            account_invoice_obj = self.env['account.move']
            account_invoice_line_obj = self.env['account.move.line']
            ir_property_obj = self.env['ir.property']
            invoice_date = date.today()
            invoice_line_list = []
            invoice_line_dict = {}
            product = self.env.ref('abs_construction_management.project_issue_product_id')
            account_id = False
            if product.id:
                account_id = product.property_account_income_id.id
            if not account_id:
                inc_acc = ir_property_obj._get('property_account_income_categ_id', 'product.category')
            for line in self.issue_line_ids:
                if line:
                    invoice_line_dict = {
                                         'product_id' : line.product_id.id,
                                         'name' : line.product_id.name,
                                         'quantity' : line.product_qty,
                                         'price_unit' : line.product_id.lst_price,
                                         'account_id' : inc_acc.id,
                                        }
                    if invoice_line_dict:
                        invoice_line_list.append((0,0, invoice_line_dict))
            new_invoice_id = account_invoice_obj.create({'partner_id' : self.supplier_id.id,
                                                         'move_type' : 'in_invoice',
                                                         'invoice_date' : invoice_date,
                                                         'project_issue_id' : self.id,
                                                         'project_id' : self.project_id.id,
                                                         'invoice_line_ids': invoice_line_list,
                                                       })
        else:
            raise ValidationError(_( "Add some invoice lines."))

class ProjectIssueLine(models.Model):
    _name = 'project.issue.line'
    _description = 'Project Issue Line'

    isuue_invoice_id = fields.Many2one('project.issue', string = 'Issue Reference ID')
    product_id = fields.Many2one('product.product', string = 'Product')
    description = fields.Char(string = 'Description')
    product_qty = fields.Float(string = 'Quantity', default = '1.00')
    price_unit = fields.Float(string = 'Unit Price', default = '0.00')
    amount_total = fields.Float(string = 'Subtotal', compute = 'compute_amount_total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        part = self.isuue_invoice_id.project_id and self.isuue_invoice_id.job_order_id
        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a Project and Work Order!'),
                }
            return {'warning': warning}
        for record in self:
            if record.product_id:
                record.update({'description': record.product_id.name, 'price_unit' : record.product_id.list_price})

    @api.depends('product_qty', 'price_unit')
    def compute_amount_total(self):
        for line in self:
            line.update({'amount_total': line.product_qty * line.price_unit})
