# -*- coding: utf-8 -*-

import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date , timedelta

class InvestigationReport(models.Model):
    _name = 'investigation.report.employee'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Investigation report'
    _order = 'create_date DESC'
    _check_company_auto = True

    READONLY_STATES = {
        'draft': [('readonly', False)],
        'process': [('readonly', False)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    employee_incident_id = fields.Many2one('incident.report.employee','Incident Report', required=True)
    investigation_ids = fields.One2many('investigation.record', 'inv_report_id')
    action_checklist_ids = fields.One2many('action.checklist', 'investigation_report_id')
    incident_category_id = fields.Many2one('incident.category','Incident category', readonly=True)
    responsible_person = fields.Many2one('hr.employee', 'Responsible Person', required=True)
    description = fields.Text(string='Description', readonly=True)
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('process', 'On investigation'),
            ('done', 'Completed'),
            ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')

    def action_process(self):
        self.state = 'process'

    def action_cancel(self):
        self.state = 'cancel'
    
    def action_complete(self):
        for record in self:
            if 'investigation' in record.investigation_ids.mapped('state'):
                raise ValidationError(_("All Investigation must be Complete"))
            record.state = 'done'

    @api.onchange('employee_incident_id')
    def _onchange_employee_incident_id(self):
        for record in self:
            if record.employee_incident_id:
                record.incident_category_id = record.employee_incident_id.incident_category_id.id
                record.description = record.employee_incident_id.description
                record.employee_id = record.employee_incident_id.employee_id.id

    @api.onchange('action_checklist_ids')
    def _onchange_action_checklist_ids(self):
        for rec in self:
            if rec.action_checklist_ids:
                for line in rec.action_checklist_ids:
                    if not line.employee_incident_id:
                        line.employee_incident_id = rec.employee_incident_id

                        if line.employee_incident_id or line.investigation_report_id:
                            app_list = []
                            if line.is_hse_action_approval_matrix:
                                line.action_checklist_user_ids = [(5, 0, 0)]
                                for approving in line.approving_matrix_action_checklist_id:
                                    for approval in approving.approval_matrix_ids:
                                        line.action_checklist_user_ids.create({
                                            'action_checklist_approver_id': line.id,
                                            'user_ids': [(6, 0, approval.approvers.ids)],
                                            'minimum_approver': approval.minimum_approver,

                                        })
                                        for approvers in approval.approvers:
                                            app_list.append(approvers.id)
                                line.approvers_ids = app_list

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('investigation.report.employee.sequence')
        return super(InvestigationReport, self).create(vals)
    

class InvestigationRecord(models.Model):
    _name = 'investigation.record'
    _description = 'Investigation Record'

    inv_report_id = fields.Many2one('investigation.report.employee','Investigation report', required=True)
    inv_datetime = fields.Datetime('Investigation Date', required=True)
    complete_datetime = fields.Datetime('Investigation Finsihed Date')
    Investigation_process = fields.Text('Investigation Process', required=True)
    Investigation_findigs = fields.Text('Investigation Findings', required=True)
    state = fields.Selection([
        ('investigation', 'On Investigation'),
        ('complete', 'Completed')], string='Status', readonly=True, copy=False, index=True, tracking=True, default='investigation')
    
    def complete(self):
        context = {
            'default_record_id': self.id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Investigation Finsihed Date',
            'res_model': 'compute.complete.date',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            "context": context,
            }
    
    @api.onchange('inv_datetime')
    def depends_inv_datetime(self):
        for res in self:
            current_date = datetime.now()
            if res.inv_datetime:
                if res.inv_datetime > current_date:
                    raise ValidationError("Can not input more than the current time.")

    