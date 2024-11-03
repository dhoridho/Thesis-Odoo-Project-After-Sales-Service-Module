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

class ProjectTask(models.Model):
    _inherit = 'project.task'

    starting_date = fields.Date(string = 'Start Date')
    notes_count = fields.Integer(string = 'Work Order Notes', compute = 'compute_notes_count')
    task_ref_name = fields.Char(string = 'Work Order Number')
    project_issue_count = fields.Integer(string = 'Work Order Issues', compute = 'compute_project_issue_count')
    equipment_request_count = fields.Integer(string = 'Equipment Request', compute = 'compute_equipment_request_count')
    vehicle_request_count = fields.Integer(string = 'Vehicle Request', compute = 'compute_vehicle_request_count')
    state = fields.Selection([('draft','Draft'),('inprogress','In Progress'),('pending','Pending'),('complete','Complete')],string = "State", readonly=True, default='draft')

    purchase_order_exempt = fields.Boolean(string = 'Purchase Order Exempt')
    purchase_order_count = fields.Integer(string = 'Purchase Order', compute = 'compute_purchase_order_count')

    purchase_order_ids = fields.One2many('purchase.order','work_order_id', string="Purchases")
    extra_material_amount = fields.Float(string="Extra Material Amount", compute="compute_amount", currency_field='currency_id')

    def action_inprogress(self):
        return self.write({'state': 'inprogress', 'purchase_order_exempt' : False})

    def action_pending(self):
        return self.write({'state': 'pending'})

    def action_complete(self):
        return self.write({'state': 'complete'})

    def compute_purchase_order_count(self):
        purchase_order_obj = self.env['purchase.order']
        for task in self:
            task.purchase_order_count = purchase_order_obj.search_count([('work_order_id', '=', task.id)])

    def compute_notes_count(self):
        job_notes_obj = self.env['job.notes']
        for task in self:
            task.notes_count = job_notes_obj.search_count([('task_id', '=', task.id)])

    def compute_project_issue_count(self):
        project_issue_obj = self.env['project.issue']
        for task in self:
            task.project_issue_count = project_issue_obj.search_count([('job_order_id', '=', task.id)])

    def compute_equipment_request_count(self):
        equipment_request_obj = self.env['equipment.request']
        for task in self:
            task.equipment_request_count = equipment_request_obj.search_count([('task_id', '=', task.id)])

    def compute_vehicle_request_count(self):
        vehicle_request_obj = self.env['vehicle.request']
        for task in self:
            task.vehicle_request_count = vehicle_request_obj.search_count([('task_id', '=', task.id)])

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].sudo().get('project.task') or ' '
        vals['task_ref_name'] = sequence
        result = super(ProjectTask, self).create(vals)

        return result

    def action_view_purchase_order(self):
        return {
                'name': _('Purchase Order'),
                'domain': [('work_order_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'purchase.order',
                'view_id': False,
                'views': [(self.env.ref('purchase.purchase_order_tree').id, 'tree'),(self.env.ref('purchase.purchase_order_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def action_view_job_notes(self):
        return {
                'name': _('Notes'),
                'domain': [('task_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'job.notes',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_job_notes_menu_tree').id, 'tree'),(self.env.ref('abs_construction_management.view_job_notes_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def action_view_project_issues(self):
        return {
                'name': _('Project Issues'),
                'domain': [('job_order_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'project.issue',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_project_issue_menu_tree').id, 'tree'),(self.env.ref('abs_construction_management.view_project_issue_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def action_view_equipment_request(self):
        return {
                'name': _('Equipment Requests'),
                'domain': [('task_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'equipment.request',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_equipment_request_menu_tree').id, 'tree'),(self.env.ref('abs_construction_management.view_equipment_request_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def action_view_vehicle_request(self):
        return {
                'name': _('Vehicle Request'),
                'domain': [('task_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'vehicle.request',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_vehicle_request_menu_tree').id, 'tree'),
                          (self.env.ref('abs_construction_management.view_vehicle_request_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def compute_amount(self):
        for task in self:
            total = 0
            if task.purchase_order_ids:
                for order in task.purchase_order_ids:
                    if order.invoice_ids:
                        for invoice in order.invoice_ids:
                            if invoice.amount_total:
                                total += invoice.amount_total
            task.extra_material_amount = total
