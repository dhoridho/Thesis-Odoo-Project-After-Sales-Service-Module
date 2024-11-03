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

class EquipmentRequest(models.Model):
    _name = 'equipment.request'
    _description = "Equipment Request"

    name = fields.Char(string = 'Name')
    project_id = fields.Many2one('project.project', string = 'Project')
    task_id = fields.Many2one('project.task', string = 'Work Order')
    task_ids = fields.Many2many('project.task', string = 'Work Orders')
    assigned_user_id = fields.Many2one('res.users', string = 'Assigned To')
    supplier_id = fields.Many2one('res.partner', string = 'Supplier')
    equipment_ids = fields.One2many('equipment.line','equipment_request_id', string = 'Equipments')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
    state = fields.Selection([('draft','Draft'),('approved','Approved'),('invoiced','Invoiced'),('done','Done')],string = "State", readonly=True, default='draft')
    invoice_amount = fields.Monetary(string = 'Invoice Amount', currency_field='currency_id', readonly = True, compute = 'compute_invoice_amount', store = True)
    total_amount = fields.Monetary(string = 'Total Amount', compute = 'compute_total_amount', store = True)
    invoice_ids = fields.One2many('account.move','equipment_invoice_id', string = 'Equiment Invoices')
    invoice_count = fields.Integer(string = 'Equipment Bill', compute = 'compute_invoice_count')

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].sudo().get('equipment.request') or ' '
        vals['name'] = sequence
        result = super(EquipmentRequest, self).create(vals)
        return result

    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id

    @api.depends('invoice_ids.amount_total')
    def compute_invoice_amount(self):
        for equipment_request in self:
            if equipment_request.invoice_ids:
                for invoice in equipment_request.invoice_ids:
                    equipment_request.invoice_amount += invoice.amount_total

    @api.depends('equipment_ids.equipment_amount')
    def compute_total_amount(self):
        for equipment_request in self:
            if equipment_request.equipment_ids or equipment_request.total_amount:
                total = 0
                for equipment in equipment_request.equipment_ids:
                    if equipment:
                        total += equipment.equipment_amount
                equipment_request.total_amount = total

    def action_approved(self):
        return self.write({'state': 'approved'})

    def action_done(self):
        if self.invoice_ids:
            for invoice in self.invoice_ids:
                if invoice.amount_residual != 0:
                    raise ValidationError(_( "Payment is remain!"))
        return self.write({'state': 'done'})

    def compute_invoice_count(self):
        account_invoice_obj = self.env['account.move']
        for equipment in self:
            equipment.invoice_count = account_invoice_obj.search_count([('equipment_invoice_id', '=', equipment.id)])

    def create_bill(self):
        if self.equipment_ids:
            account_invoice_obj = self.env['account.move']
            account_invoice_line_obj = self.env['account.move.line']
            ir_property_obj = self.env['ir.property']
            invoice_date = date.today()
            invoice_line_list = []
            invoice_line_dict = {}
            product = self.env.ref('abs_construction_management.equipment_request_product_id')
            account_id = False
            if product.id:
                account_id = product.property_account_income_id.id
            if not account_id:
                inc_acc = ir_property_obj._get('property_account_income_categ_id', 'product.category')
            for line in self.equipment_ids:
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

            new_invoice_id = account_invoice_obj.create({
                                                         'partner_id' : self.supplier_id.id,
                                                         'move_type' : 'in_invoice',
                                                         'invoice_date' : invoice_date,
                                                         'invoice_origin' : self.name,
                                                         'equipment_invoice_id' : self.id,
                                                         'project_id' : self.project_id.id,
                                                         'invoice_line_ids': invoice_line_list,
                                                       })
            
            self.write({'state': 'invoiced'})
        else:
            raise ValidationError(_( "Add some equipment lines."))

    def action_view_invoice(self):
        return {
                'name': _('Invoice'),
                'domain': [('equipment_invoice_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [(self.env.ref('account.view_invoice_tree').id, 'tree'), (self.env.ref('account.view_move_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    @api.onchange('project_id')
    def onchange_project_id(self):
        if self.project_id:
            task_list = []
            task_obj = self.env['project.task'].search([('project_id','=',self.project_id.id)])
            if task_obj:
                for task in task_obj:
                    if task:
                        task_list.append(task)
                if task_list:
                    self.task_ids = [(6,0,[v.id for v in task_list])]

    @api.onchange('task_id')
    def onchange_task_id(self):
        if self.task_id:
            self.assigned_user_id = self.task_id.user_id.id
            self.supplier_id = self.task_id.partner_id.id

class EquipmentLine(models.Model):
    _name = 'equipment.line'
    _description = "Equipment Line"

    equipment_request_id = fields.Many2one('equipment.request', string = 'Reference ID')
    product_id = fields.Many2one('product.product', string = 'Product')
    description = fields.Char(string = 'Description')
    product_qty = fields.Float(string = 'Quantity', default = '1.00')
    price_unit = fields.Float(string = 'Unit Price', default = '0.00')
    equipment_amount = fields.Float(string = 'Subtotal', compute='compute_equipment_amount')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for record in self:
            part = record.equipment_request_id.project_id and record.equipment_request_id.task_id
            if not part:
                warning = {
                           'title': _('Warning!'),
                           'message': _('You must first select a Project and Work Order!'),
                          }
                return {'warning': warning}
            if record.product_id:
                record.update({'description': record.product_id.name, 'price_unit' : record.product_id.list_price})

    @api.depends('product_qty', 'price_unit')
    def compute_equipment_amount(self):
        for line in self:
            line.update({'equipment_amount': line.product_qty * line.price_unit})
