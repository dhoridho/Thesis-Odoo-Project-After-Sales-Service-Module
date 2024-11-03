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

class ProjectProject(models.Model):
    _inherit = 'project.project'

    cost_sheet_count = fields.Integer(string = 'Cost Sheet', compute = '_comute_cost_sheet')
    notes_count = fields.Integer(string = 'Notes', compute = '_comute_notes_count')
    estimation_sheet_cost = fields.Monetary(string = 'Estimation Cost', currency_field='currency_id', compute = 'compute_estimation_sheet_cost', store = True)
    equipment_cost = fields.Float(string = 'Equipment Cost', compute = 'compute_equipment_cost', currency_field='currency_id', store = True)
    vehicle_cost = fields.Float(string = 'Vehicle Cost', compute = 'compute_vehicle_cost', currency_field='currency_id', store = True)
    project_issue_cost = fields.Float(string = 'Project Issue Cost', compute = 'compute_project_issue_cost', currency_field='currency_id', store = True)
    extra_material_cost = fields.Float(string="Extra Material Cost", compute="compute_extra_material_cost", currency_field='currency_id')
    invoice_ids = fields.One2many('account.move','project_id', string = 'Project Invoices')
    invoice_count = fields.Integer(string = 'Bills', compute = 'compute_invoices')

    cost_sheet_ids = fields.One2many('job.cost.sheet','project_id', string = 'Cost Sheets')
    total_amount = fields.Monetary(string = 'Total Costing', currency_field='currency_id', compute = 'compute_total_amount', store = True)

    @api.depends('invoice_ids.amount_total','cost_sheet_ids.amount_total','task_ids.extra_material_amount')
    def compute_total_amount(self):
        for project in self:
            total = 0
            estimation_cost = 0
            total_cost = 0
            if project.cost_sheet_ids:
                for cost_sheet in project.cost_sheet_ids:
                    estimation_cost += cost_sheet.amount_total
            if project.invoice_ids:
                for invoice in project.invoice_ids:
                    total += invoice.amount_total
            if project.task_ids:
                for extra_cost in project.task_ids:
                    total_cost += extra_cost.extra_material_amount
            project.total_amount = total + estimation_cost + total_cost

    def compute_invoices(self):
        account_invoice_obj = self.env['account.move']
        for project in self:
            if project:
                project.invoice_count = account_invoice_obj.search_count([('project_id', '=', project.id)])

    @api.depends('cost_sheet_ids.amount_total')
    def compute_estimation_sheet_cost(self):
        for project in self:
            job_cost_sheet_obj = self.env['job.cost.sheet'].search([('project_id','=',project.id)])
            if job_cost_sheet_obj:
                total = 0
                for cost_sheet in job_cost_sheet_obj:
                    if cost_sheet:
                        total += cost_sheet.amount_total
                project.estimation_sheet_cost = total

    @api.depends('invoice_ids.amount_total')
    def compute_equipment_cost(self):
        for project in self:
            equipment_request_obj = self.env['equipment.request'].search([('project_id','=',project.id)])
            if equipment_request_obj:
                total = 0
                for equipment in equipment_request_obj:
                    if equipment:
                        account_invoice_obj = self.env['account.move'].search([('invoice_origin','=',equipment.name)])
                        if account_invoice_obj:
                            for invoice in account_invoice_obj:
                                if invoice:
                                    total += invoice.amount_total
                project.equipment_cost = total

    @api.depends('invoice_ids.amount_total')
    def compute_vehicle_cost(self):
        for project in self:
            vehicle_request_obj = self.env['vehicle.request'].search([('project_id','=',project.id)])
            if vehicle_request_obj:
                total = 0
                for vehicle in vehicle_request_obj:
                    if vehicle:
                        account_invoice_obj = self.env['account.move'].search([('invoice_origin','=',vehicle.name)])
                        if account_invoice_obj:
                            for invoice in account_invoice_obj:
                                if invoice:
                                    total += invoice.amount_total
                project.vehicle_cost = total

    @api.depends('invoice_ids.amount_total')
    def compute_project_issue_cost(self):
        for project in self:
            project_issue_obj = self.env['project.issue'].search([('project_id','=',project.id)])
            if project_issue_obj:
                total = 0
                for issue in project_issue_obj:
                    if issue:
                        account_invoice_obj = self.env['account.move'].search([('project_issue_id','=',issue.id)])
                        if account_invoice_obj:
                            for invoice in account_invoice_obj:
                                if invoice:
                                    total += invoice.amount_total
                project.project_issue_cost = total

    def _comute_cost_sheet(self):
        for project in self:
            job_cost_sheet_obj = self.env['job.cost.sheet'].search([('project_id','=',project.id)])
            count = 0
            if job_cost_sheet_obj:
                for sheet in job_cost_sheet_obj:
                    if sheet:
                        count += 1
            project.cost_sheet_count = count

    @api.depends('task_ids.extra_material_amount')
    def compute_extra_material_cost(self):
        for project in self:
            total = 0
            if project.task_ids:
                for task in project.task_ids:
                    if task.extra_material_amount:
                        total += task.extra_material_amount
            project.extra_material_cost = total

    def _comute_notes_count(self):
        for project in self:
            project_notes_obj = self.env['project.notes'].search([('project_id','=',project.id)])
            count = 0
            if project_notes_obj:
                for note in project_notes_obj:
                    if note:
                        count += 1
            project.notes_count = count

    def action_view_cost_sheet(self):
        return {
                'name': _('Cost Sheet'),
                'domain': [('project_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'job.cost.sheet',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_job_cost_sheet_menu_tree').id, 'tree'),(self.env.ref('abs_construction_management.view_job_cost_sheet_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def action_view_project_notes(self):
        return {
                'name': _('Notes'),
                'domain': [('project_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'project.notes',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_project_notes_menu_tree').id, 'tree'),(self.env.ref('abs_construction_management.view_project_notes_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }

    def action_view_invoices(self):
        return {
                'name': _('Invoices'),
                'domain': [('project_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [(self.env.ref('account.view_move_tree').id, 'tree'),(self.env.ref('account.view_move_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }
