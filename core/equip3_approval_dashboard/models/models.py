# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class ApprovalDashboardReport(models.Model):
    _name = "approval.dashboard.report"
    _description = "Approval dashboard"



    name = fields.Char('Number')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    applied_date = fields.Date('Applied Date')
    state = fields.Char(string='Status')
    model_name = fields.Char("Model Name")
    count = fields.Integer("Count",default=1)


    @api.model
    def action_dashboard_redirect(self):
        
        return self.env.ref('equip3_approval_dashboard.rr_approval_dashboard_board').read()[0]


class ApprovalDashboardReportConfig(models.Model):
    _name = "approval.dashboard.report.config"
    _description = "Approval dashboard Config"
    _order = 'sequence'


    name = fields.Char("Name")
    sequence = fields.Integer("Sequence")
    model_id = fields.Many2one("ir.model","Obj Approval")
    model_approval_id = fields.Many2one("ir.model","Obj Relation")
    approval_field_id = fields.Many2one("ir.model.fields","Relation Field")
    approval_number_field_id = fields.Many2one("ir.model.fields","Number Field")
    approval_employee_field_id = fields.Many2one("ir.model.fields","Employee Field")
    approval_state_field_id = fields.Many2one("ir.model.fields","Status Field")
    model_state_id = fields.Many2one("ir.model.fields", "Parent Status Field")


    @api.onchange('approval_field_id')
    def onchange_approval_field_id(self):
        obj = self.env['ir.model']
        if self.approval_field_id.relation:
            relation = obj.search([('model','=',self.approval_field_id.relation)],limit=1)
            self.model_approval_id = relation.id
            state = self.env['ir.model.fields'].sudo().search([('name', 'in', ['state', 'status']), ('model', '=', self.model_approval_id.model), ('ttype', '=', 'selection')], limit=1)
            self.model_state_id = state
        else:
            self.model_approval_id = False

    @api.onchange('model_id')
    def onchange_model_id(self):
        self.approval_field_id = False
        self.approval_number_field_id = False
        self.approval_employee_field_id = False
        self.approval_state_field_id = False
