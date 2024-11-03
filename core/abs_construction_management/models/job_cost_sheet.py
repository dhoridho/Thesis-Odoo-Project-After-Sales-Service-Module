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
from datetime import datetime, date
from odoo.exceptions import ValidationError

class JobCostSheet(models.Model):
    _name = 'job.cost.sheet'
    _description = "Job Cost Sheet"

    name = fields.Char("Sheet Number")
    cost_sheet_name = fields.Char(string = 'Name',required = True)
    project_id = fields.Many2one('project.project', string = 'Project')
    supplier_id = fields.Many2one('res.partner', string = 'Supplier', required = True)
    close_date = fields.Datetime(string = 'Close Date', readonly = True)
    user_id = fields.Many2one('res.users', string = 'Created By')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
    purchase_exempt = fields.Boolean(string = 'Purchase Exempt', copy=False)
    description = fields.Text(string = 'Extra Information')

    material_ids = fields.One2many('material.material','job_sheet_id', string = 'Materials', states={'purchase': [('readonly', True)], 'done': [('readonly', True)]})
    material_labour_ids = fields.One2many('material.labour','job_sheet_id', string = 'Labour', states={'purchase': [('readonly', True)], 'done': [('readonly', True)]})
    material_overhead_ids = fields.One2many('material.overhead','job_sheet_id', string = 'Overhead', states={'purchase': [('readonly', True)], 'done': [('readonly', True)]})

    amount_material = fields.Monetary(string='Material Cost', readonly=True, compute = '_amount_material')
    amount_labour = fields.Monetary(string='Labour Cost', readonly=True, compute = '_amount_labour')
    amount_overhead = fields.Monetary(string='Overhead Cost', readonly=True, compute = '_amount_overhead')

    amount_total = fields.Monetary(string='Total Cost', readonly=True, compute = '_amount_total', store = True)
    state = fields.Selection([('draft','Draft'),('approved','Approved'),('purchase','Purchase Order'),('done','Done')],string = "State", readonly=True, default='draft')

    purchase_order_ids = fields.One2many('purchase.order','job_cost_sheet_id', string = 'Purchase Orders')
    purchase_order_count = fields.Integer(string = 'Purchases', compute = '_purchase_order_count')

    def action_view_purchase_order(self):
        return {
                'name': _('Purchase order'),
                'domain': [('id','in',[x.id for x in self.purchase_order_ids])],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'view_id': False,
                'views': [(self.env.ref('purchase.purchase_order_tree').id, 'tree'), (self.env.ref('purchase.purchase_order_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def _purchase_order_count(self):
        total = 0
        for order in self.purchase_order_ids:
            if order:
                total += 1
        self.purchase_order_count = total

    def create_purchase_order(self):
        if self.supplier_id:
            purchase_order_obj = self.env['purchase.order']
            purchase_order_line_obj = self.env['purchase.order.line']
            cost_sheet_dict = { 'partner_id' :  self.supplier_id.id, 'job_cost_sheet_id' : self.id }
            if cost_sheet_dict:
                new_purchase_order_id = purchase_order_obj.create(cost_sheet_dict)
            if self.material_ids:
                for material in self.material_ids:
                    if material.product_id:
                        material_material_dict = { 'order_id' : new_purchase_order_id.id,
                                                   'product_id' : material.product_id.id,
                                                   'price_unit' : material.price_unit,
                                                   'name' : material.product_id.description,
                                                   'date_planned' : datetime.today(),
                                                   'name' : material.product_id.name,
                                                   'product_qty' : material.product_qty,
                                                   'product_uom': material.product_id.uom_id.id }
                        purchase_order_line_obj.create(material_material_dict)
            if self.material_labour_ids:
                for labour in self.material_labour_ids:
                    if labour.product_id:
                        material_labour_dict = { 'order_id' : new_purchase_order_id.id,
                                                 'product_id' : labour.product_id.id,
                                                 'price_unit' : labour.price_unit,
                                                 'name' : labour.product_id.description,
                                                 'date_planned' : datetime.today(),
                                                 'name' : labour.product_id.name,
                                                 'product_qty' : labour.product_qty,
                                                 'product_uom': labour.product_id.uom_id.id }
                        purchase_order_line_obj.create(material_labour_dict)
            if self.material_overhead_ids:
                for overhead in self.material_overhead_ids:
                    if overhead.product_id:
                        material_overhead_dict = { 'order_id' : new_purchase_order_id.id,
                                                   'product_id' : overhead.product_id.id,
                                                   'price_unit' : overhead.price_unit,
                                                   'name' : overhead.product_id.description,
                                                   'date_planned' : datetime.today(),
                                                   'name' : overhead.product_id.name,
                                                   'product_qty' : overhead.product_qty,
                                                   'product_uom': overhead.product_id.uom_id.id }
                        purchase_order_line_obj.create(material_overhead_dict)
            self.update({ 'purchase_exempt' : True, 'state' : 'purchase' })

    def _compute_currency(self):
        self.currency_id = self.company_id.currency_id

    def action_approved(self):
        if not self.material_ids and not self.material_labour_ids and not self.material_overhead_ids:
            raise ValidationError(_( "Add at least one material for estimation."))
        return self.write({'state': 'approved'})

    def action_done(self):
        return self.write({'state': 'done', 'close_date' : datetime.now()})

    @api.model
    def create(self,vals):
        sequence = self.env['ir.sequence'].sudo().get('job.cost.sheet') or ' '
        vals['name'] = sequence
        result = super(JobCostSheet, self).create(vals)

        return result

    @api.depends('material_ids.material_amount_total')
    def _amount_material(self):
        for sheet in self:
            amount_material = 0.0
            for line in sheet.material_ids:
                amount_material += line.material_amount_total
            sheet.update({'amount_material': round(amount_material)})

    @api.depends('material_labour_ids.labour_amount_total')
    def _amount_labour(self):
        for sheet in self:
            amount_labour = 0.0
            for line in sheet.material_labour_ids:
                amount_labour += line.labour_amount_total
            sheet.update({'amount_labour': round(amount_labour)})

    @api.depends('material_overhead_ids.overhead_amount_total')
    def _amount_overhead(self):
        for sheet in self:
            amount_overhead = 0.0
            for line in sheet.material_overhead_ids:
                amount_overhead += line.overhead_amount_total
            sheet.update({'amount_overhead': round(amount_overhead)})

    @api.depends('material_ids.material_amount_total','material_labour_ids.labour_amount_total','material_overhead_ids.overhead_amount_total')
    def _amount_total(self):
        for cost_sheet in self:
            amount_material = 0.0
            amount_labour = 0.0
            amount_overhead = 0.0
            for line in cost_sheet.material_ids:
                amount_material += line.material_amount_total
            for line in cost_sheet.material_labour_ids:
                amount_labour += line.labour_amount_total
            for line in cost_sheet.material_overhead_ids:
                amount_overhead += line.overhead_amount_total
            cost_sheet.amount_total = (amount_material + amount_labour + amount_overhead)

class MaterialMaterial(models.Model):
    _name = 'material.material'
    _description = "Material"

    job_sheet_id = fields.Many2one('job.cost.sheet', string = 'Job Sheet')
    product_id = fields.Many2one('product.product', string = 'Product')
    description = fields.Char(string = 'Description')
    product_qty = fields.Float(string = 'Ordered Quantity', default = '1.00')
    price_unit = fields.Float(string = 'Unit Price', default = '0.00')
    material_amount_total = fields.Float(string = 'Subtotal', compute = 'compute_material_amount_total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.update({'description': record.product_id.name, 'price_unit' : record.product_id.list_price})

    @api.depends('product_qty', 'price_unit')
    def compute_material_amount_total(self):
        for line in self:
            line.update({'material_amount_total': line.product_qty * line.price_unit})


class MaterialLabour(models.Model):
    _name = 'material.labour'
    _description = "Labour"

    job_sheet_id = fields.Many2one('job.cost.sheet', string = 'Job Sheet')
    product_id = fields.Many2one('product.product', string = 'Product')
    description = fields.Char(string = 'Description')
    product_qty = fields.Float(string = 'Ordered Quantity', default = '1.00')
    price_unit = fields.Float(string = 'Unit Price', default = '0.00')
    labour_amount_total = fields.Float(string = 'Subtotal', compute = 'compute_labour_amount_total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.update({'description': record.product_id.name, 'price_unit' : record.product_id.list_price})

    @api.depends('product_qty', 'price_unit')
    def compute_labour_amount_total(self):
        for line in self:
            line.update({'labour_amount_total': line.product_qty * line.price_unit})

class MaterialOverhead(models.Model):
    _name = 'material.overhead'
    _description = "Overhead"

    job_sheet_id = fields.Many2one('job.cost.sheet', string = 'Job Sheet')
    product_id = fields.Many2one('product.product', string = 'Product')
    description = fields.Char(string = 'Description')
    product_qty = fields.Float(string = 'Ordered Quantity', default = '1.00')
    price_unit = fields.Float(string = 'Unit Price', default = '0.00')
    overhead_amount_total = fields.Float(string = 'Subtotal', compute = 'compute_overhead_amount_total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.update({'description': record.product_id.name, 'price_unit' : record.product_id.list_price})

    @api.depends('product_qty', 'price_unit')
    def compute_overhead_amount_total(self):
        for line in self:
            line.update({'overhead_amount_total': line.product_qty * line.price_unit})

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    job_cost_sheet_id = fields.Many2one('job.cost.sheet', string = 'Job Cost Sheet')
    work_order_id = fields.Many2one('project.task', string = 'Work order')
