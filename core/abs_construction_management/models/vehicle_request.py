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

class VehicleRequest(models.Model):
    _name = 'vehicle.request'
    _description = "Vehicle Request"

    name = fields.Char(string = 'Name')
    project_id = fields.Many2one('project.project', string = 'Project')
    task_id = fields.Many2one('project.task', string = 'Work Order')
    task_ids = fields.Many2many('project.task', string = 'Work Orders')
    vehicle_id = fields.Many2one('product.product', string = 'Vehicle')
    driver_id = fields.Many2one('hr.employee', string = 'Driver')
    duration = fields.Float(string = 'Duration')
    supplier_id = fields.Many2one('res.partner', string = 'Supplier')
    rent = fields.Float(string = 'Rent')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
    state = fields.Selection([('draft','Draft'),('approved','Approved'),('invoiced','Invoiced'),('done','Done')],string = "State", readonly=True, default='draft')
    invoice_ids = fields.One2many('account.move','vehicle_invoice_id', string = 'Vehicle Invoices')
    invoice_count = fields.Integer(string = 'Vehicle Bill', compute = 'compute_invoice_count')

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].sudo().get('vehicle.request') or ' '
        vals['name'] = sequence
        result = super(VehicleRequest, self).create(vals)

        return result

    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id

    def action_approved(self):
        if not self.driver_id:
            raise ValidationError(_( "Add Driver"))
        return self.write({'state': 'approved'})

    def action_done(self):
        if self.invoice_ids:
            for invoice in self.invoice_ids:
                if invoice.amount_residual != 0:
                    raise ValidationError(_( "Payment is remain!"))
        return self.write({'state': 'done'})

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
            self.supplier_id = self.task_id.partner_id.id

    @api.onchange('vehicle_id')
    def onchange_vehicle_id(self):
        if self.vehicle_id:
            self.rent = self.vehicle_id.rent_per_hours

    def compute_invoice_count(self):
        account_invoice_obj = self.env['account.move']
        for vehicle in self:
            vehicle.invoice_count = account_invoice_obj.search_count([('vehicle_invoice_id', '=', vehicle.id)])

    def create_vendor_bill(self):
        if self.vehicle_id:
            account_invoice_obj = self.env['account.move']
            account_invoice_line_obj = self.env['account.move.line']
            ir_property_obj = self.env['ir.property']
            invoice_date = date.today()
            product = self.env.ref('abs_construction_management.vehicle_request_product_id')
            account_id = False
            if product.id:
                account_id = product.property_account_income_id.id
            if not account_id:
                inc_acc = ir_property_obj._get('property_account_income_categ_id', 'product.category')

            new_invoice_id = account_invoice_obj.create({
                                                         'partner_id' : self.supplier_id.id,
                                                         'move_type' : 'in_invoice',
                                                         'invoice_date' : invoice_date,
                                                         'invoice_origin' : self.name,
                                                         'vehicle_invoice_id' : self.id,
                                                         'project_id' : self.project_id.id,
                                                         'invoice_line_ids': [(0,0,{
                                                                                    'product_id': self.vehicle_id.id,
                                                                                    'name'      : self.vehicle_id.name,
                                                                                    'quantity'  : self.duration,
                                                                                    'price_unit': self.vehicle_id.rent_per_hours,
                                                                                    'account_id': inc_acc.id,
                                                                                   })],
                                                           })
            self.write({'state': 'invoiced'})

    def action_view_invoice(self):
        return {
                'name': _('Invoice'),
                'domain': [('vehicle_invoice_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [(self.env.ref('account.view_invoice_tree').id, 'tree'), (self.env.ref('account.view_move_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }
