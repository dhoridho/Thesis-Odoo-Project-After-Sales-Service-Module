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
from datetime import date,datetime
from odoo.exceptions import ValidationError

class WorkOrderPurchaseOrder(models.TransientModel):
    _name = 'workorder.purchase.order'
    _description = 'Workorder Purchase Order'

    project_id = fields.Many2one('project.project',string = "Project", readonly = True)
    work_order_id = fields.Many2one('project.task', string = 'Work Order', readonly = True)
    supplier_id = fields.Many2one('res.partner', string = 'Supplier')
    material_ids = fields.One2many('workorder.material','ref_work_order_id', string = 'Materials')

    @api.model
    def default_get(self, fields):
        rec = super(WorkOrderPurchaseOrder, self).default_get(fields)
        Move = self.env['project.task']
        if self.env.context.get('active_id'):
            work_order_id = Move.browse(self.env.context['active_ids'])

            rec.update({ 'project_id':  work_order_id.project_id.id, 'work_order_id' : work_order_id.id,})

            return rec

    def create_purchase_order(self):
        if self.work_order_id:
            project_task_obj = self.env['project.task']
            if self.env.context.get('active_id'):
                work_order_id = project_task_obj.browse(self.env.context['active_ids'])
            purchase_order_obj = self.env['purchase.order']
            purchase_order_line_obj = self.env['purchase.order.line']

            new_purchase_order_id = purchase_order_obj.create({ 'partner_id' : self.supplier_id.id,
                                                                'work_order_id' : work_order_id.id,
                                                              })

            if self.material_ids:
                for material in self.material_ids:
                    if material:
                        new_purchase_order_line_id = purchase_order_line_obj.create({ 'order_id' : new_purchase_order_id.id,
                                                                                      'product_id' : material.product_id.id,
                                                                                      'product_uom_qty' : material.product_qty,
                                                                                      'name' : material.product_id.name,
                                                                                      'product_qty' : material.product_qty,
                                                                                      'price_unit' : material.price_unit,
                                                                                      'product_uom': material.product_id.uom_id.id,
                                                                                      'date_planned' : datetime.today(),
                                                                                    })
                work_order_id.write({ 'purchase_order_exempt' : True })
            else:
                raise ValidationError(_( "Add at least one material."))

class WorkOrderMaterial(models.TransientModel):
    _name = 'workorder.material'
    _description = 'Workorder Material'

    ref_work_order_id = fields.Many2one('workorder.purchase.order', string = 'Reference Work Order')
    product_id = fields.Many2one('product.product', string = 'Product')
    description = fields.Char(string = 'Description')
    product_qty = fields.Float(string = 'Ordered Quantity', default = '1.00')
    price_unit = fields.Float(string = 'Unit Price', default = '0.00')
    amount_total = fields.Float(string = 'Sub Total', compute = 'compute_amount_total')

    @api.onchange('product_id')
    def onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.update({'description': record.product_id.name, 'price_unit' : record.product_id.list_price})

    @api.depends('product_qty', 'price_unit')
    def compute_amount_total(self):
        for line in self:
            line.update({'amount_total': line.product_qty * line.price_unit})
