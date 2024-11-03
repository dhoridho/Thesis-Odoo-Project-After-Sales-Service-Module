# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeOnboarding(models.Model):
    _inherit = 'employee.orientation'
    _description = "Employee Onboarding"

    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_name.job_id',
                             domain="[('department_id', '=', department)]")
    employee_company = fields.Many2one('res.company', string='Company', required=True,
                                       default=lambda self: self.env.company)
    start_date_onboarding = fields.Date('Start Date')
    end_date_onboarding = fields.Date('End Date')
    orientation_id = fields.Many2one(required=False)
    entry_checklist_id = fields.Many2one('employee.entry.checklist', string='Entry Checklist',
                                     domain="[('department_ids','in', [department])]", required=True)
    checklist_line_ids = fields.One2many('onboarding.entry.checklist', 'emp_onboarding_id', string="Checklist Line")
    elearning_line_ids = fields.One2many('elearning.line', 'emp_onboarding_id', string='ELearning')
    conduct_line_ids = fields.One2many('training.conduct', 'emp_onboarding_id', string='Training')
    scoring_progress_ids = fields.One2many('onboarding.scoring.progress', 'emp_onboarding_id', string='Scoring Progress')
    total_entry_weightage = fields.Float('Total Entry Weightage', compute='_compute_total_entry_weightage', store=True)
    total_current_entry_weight = fields.Float('Current Progress', compute='_compute_total_current_entry_weight')
    document_count = fields.Integer(compute='_document_count', string="Onboarding's Document")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_company', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeOnboarding, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_company', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeOnboarding, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def write(self, vals):
        res = super(EmployeeOnboarding, self).write(vals)
        for rec in self:
            for line in rec.checklist_line_ids:
                emp_checklist = self.env['employee.checklist.line'].search([('line_id','=',line.id),('employee_id','=',rec.employee_name.id)])
                if line.state == 'completed':
                    emp_checklist.check = True
                else:
                    emp_checklist.check = False
            for line in rec.conduct_line_ids:
                emp_training = self.env['employee.training.line'].search([('line_id','=',line.id),('employee_id','=',rec.employee_name.id)])
                if line.state == 'approved':
                    emp_training.check = True
                else:
                    emp_training.check = False
            for line in rec.elearning_line_ids:
                emp_elearning = self.env['employee.elearning.line'].search([('line_id','=',line.id),('employee_id','=',rec.employee_name.id)])
                if line.progress == int(100):
                    emp_elearning.check = True
                else:
                    emp_elearning.check = False
        return res

    def custom_menu(self):
        views = [(self.env.ref('employee_orientation.view_employee_orientation_tree').id, 'tree'),
                 (self.env.ref('employee_orientation.view_employee_orientation_form').id, 'form')]
        search_view_id = self.env.ref('employee_orientation.view_employee_orientation_search').id
        if self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group \
                    ('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Onboarding',
                'res_model': 'employee.orientation',
                'view_mode': 'tree,form',
                'views': views,
                'search_view_id': search_view_id,
                'domain': [('employee_name.user_id', '=', self.env.user.id)]
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Onboarding',
                'res_model': 'employee.orientation',
                'view_mode': 'tree,form',
                'views': views,
                'search_view_id': search_view_id,
            }

    @api.onchange('employee_name')
    def onchange_elearning_line(self):
        for rec in self:
            if rec.elearning_line_ids:
                remove = []
                for line in rec.elearning_line_ids:
                    remove.append((2, line.id))
                rec.elearning_line_ids = remove
            if rec.employee_name.job_id and rec.employee_name.job_id.e_learning_required_ids:
                elearnings = []
                elearn = rec.employee_name.job_id.e_learning_required_ids
                for line in elearn:
                    elearnings.append((0, 0, {'course_id': line.id}))
                rec.elearning_line_ids = elearnings

            if rec.conduct_line_ids:
                remove = []
                for line in rec.conduct_line_ids:
                    remove.append((2, line.id))
                rec.conduct_line_ids = remove
            if rec.employee_name.job_id and rec.employee_name.job_id.course_ids:
                trainings = []
                training = rec.employee_name.job_id.course_ids
                for line in training:
                    trainings.append((0, 0, {'course_id': line.id,'employee_id': rec.employee_name.id,'conduct_line_ids': [(0, 0, {'employee_id': rec.employee_name.id, 'employee_domain_ids': [(6,0,[rec.employee_name.id])]})]}))
                rec.conduct_line_ids = trainings
                for conduct_line in rec.conduct_line_ids:
                    if conduct_line.stage_course_domain_ids:
                        conduct_line.stage_course_id = conduct_line.stage_course_domain_ids[0]._origin.id
                        conduct_line.stage_id = conduct_line.stage_course_domain_ids[0]._origin.stage_id.id

    @api.onchange('entry_checklist_id')
    def onchange_entry_checklist(self):
        for rec in self:
            rec.checklist_line_ids = [(5,0,0)]
            entry_checklist = []
            for line in rec.entry_checklist_id.checklist_line_ids:
                entry_checklist.append((0, 0, {'checklist_id': line.id,'document_type': line.document_type,'activity_type': line.activity_type,'responsible_user_id': line.responsible_user_id.id}))
            rec.checklist_line_ids = entry_checklist

    @api.onchange('name')
    def _onchange_name(self):
        for rec in self:
            line_list = []
            line_list.append((0,0,{'onboarding_component':"ENTRY CHECKLIST"}))
            line_list.append((0,0,{'onboarding_component':"TRAINING"}))
            line_list.append((0,0,{'onboarding_component':"ELEARNING"}))
            rec.scoring_progress_ids = line_list
    
    @api.onchange('scoring_progress_ids')
    def _onchange_scoring_progress_ids(self):
        for record in self:
            if record.scoring_progress_ids:
                total = sum([line.onboarding_weightage for line in record.scoring_progress_ids])
                if total > 100:
                    raise ValidationError("Maximum Total Weightage is 100. Please re-enter the value for each component !")

    @api.depends('scoring_progress_ids','scoring_progress_ids.onboarding_weightage')
    def _compute_total_entry_weightage(self):
        for rec in self:
            if rec.scoring_progress_ids:
                total = sum([data.onboarding_weightage for data in rec.scoring_progress_ids])
                rec.total_entry_weightage = total
            else:
                rec.total_entry_weightage = 0
    
    @api.depends('scoring_progress_ids','scoring_progress_ids.onboarding_weightage','checklist_line_ids','checklist_line_ids.state','conduct_line_ids','conduct_line_ids.state','elearning_line_ids','elearning_line_ids.progress')
    def _compute_total_current_entry_weight(self):
        for rec in self:
            total = 0
            if rec.checklist_line_ids:
                checklist_weightage = sum(self.scoring_progress_ids.filtered(lambda r: r.onboarding_component == 'ENTRY CHECKLIST').mapped("onboarding_weightage"))
                checklist_done = len(rec.checklist_line_ids.filtered(lambda r: r.state == 'completed'))
                all_checklist = len(rec.checklist_line_ids)
                component_checklist = (checklist_done/all_checklist) * checklist_weightage
                total += component_checklist
            if rec.conduct_line_ids:
                training_weightage = sum(self.scoring_progress_ids.filtered(lambda r: r.onboarding_component == 'TRAINING').mapped("onboarding_weightage"))
                training_done = len(rec.conduct_line_ids.filtered(lambda r: r.state == 'approved'))
                all_training = len(rec.conduct_line_ids)
                component_training = (training_done/all_training) * training_weightage
                total += component_training
            if rec.elearning_line_ids:
                elearning_weightage = sum(self.scoring_progress_ids.filtered(lambda r: r.onboarding_component == 'ELEARNING').mapped("onboarding_weightage"))
                elearning_done = len(rec.elearning_line_ids.filtered(lambda r: r.progress == int(100)))
                all_elearning = len(rec.elearning_line_ids)
                component_elearning = (elearning_done/all_elearning) * elearning_weightage
                total += component_elearning
            rec.total_current_entry_weight = total
            rec.employee_name.onboarding_progress = total

            if rec.total_entry_weightage > 0 and rec.total_current_entry_weight == rec.total_entry_weightage and rec.state == 'confirm':
                rec.write({'state': 'complete'})


    def confirm_orientation(self):
        if self.employee_name.onboarding_entry_checklist_ids:
            self.employee_name.onboarding_entry_checklist_ids = [(5,0,0)]
        for rec in self.checklist_line_ids:
            if rec.state == 'completed':
                check = True
            else:
                check = False
            self.env['employee.checklist.line'].create({
                'line_id': rec.id,
                'employee_id': self.employee_name.id,
                'name': rec.checklist_id.name,
                'check': check,
            })
        if self.employee_name.onboarding_training_ids:
            self.employee_name.onboarding_training_ids = [(5,0,0)]
        for rec in self.conduct_line_ids:
            if rec.state == 'approved':
                check = True
            else:
                check = False
            self.env['employee.training.line'].create({
                'line_id': rec.id,
                'employee_id': self.employee_name.id,
                'name': rec.course_id.name,
                'check': check,
            })
        if self.employee_name.onboarding_elearning_ids:
            self.employee_name.onboarding_elearning_ids = [(5,0,0)]
        for rec in self.elearning_line_ids:
            if rec.progress == int(100):
                check = True
            else:
                check = False
            self.env['employee.elearning.line'].create({
                'line_id': rec.id,
                'employee_id': self.employee_name.id,
                'name': rec.course_id.name,
                'check': check,
            })
        self.write({'state': 'confirm'})

    def complete_orientation(self):
        res = super(EmployeeOnboarding, self).complete_orientation()
        checklist_line = self.checklist_line_ids.filtered(lambda r: r.activity_type == 'upload_document' and r.attachment)
        if checklist_line:
            number = 1
            for rec in checklist_line:
                doc_number = self.name + "/" + str(number)
                binary = self.env["ir.attachment"].sudo().search([("res_model", "=", "onboarding.entry.checklist"),("res_id", "=", rec.id),("res_field", "=", "attachment")],limit=1)
                if binary:
                    self.env['hr.employee.document'].create({
                        'onboarding_id': self.id,
                        'name': doc_number,
                        'checklist_document_id': rec.checklist_id.id,
                        'employee_ref': self.employee_name.id,
                        'issue_date': self.end_date_onboarding,
                        'doc_attachment_id': [(4, file.id) for file in binary],
                    })
                    number += 1
        return res

    def _document_count(self):
        for rec in self:
            document_ids = self.env['hr.employee.document'].sudo().search([('onboarding_id', '=', rec.id)])
            rec.document_count = len(document_ids)
    
    def document_view(self):
        self.ensure_one()
        domain = [
            ('onboarding_id', '=', self.id)]
        return {
            'name': _("Onboarding's Document"),
            'domain': domain,
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('equip3_hr_employee_onboarding.employee_documents_onboarding_tree_view').id, 'tree'), (self.env.ref('equip3_hr_employee_onboarding.employee_document_onboarding_form_view').id, 'form')],
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref': %s}" % self.employee_name.id
        }

class ElearningLine(models.Model):
    _name = 'elearning.line'

    emp_onboarding_id = fields.Many2one('employee.orientation', string="Employee Onboarding Id")
    course_id = fields.Many2one('slide.channel', string="ELearning Course")
    user_id = fields.Many2one('res.users', string="Responsible", related='course_id.user_id')
    expected_date = fields.Date(string="Expected Date")
    progress = fields.Integer(string='Progress', compute='_compute_progress')
    state = fields.Selection([('new', 'New'), ('done', 'Done')], default='new', string="Status")

    @api.depends('emp_onboarding_id')
    def _compute_progress(self):
        for rec in self:
            elearning_data = self.env['slide.channel.partner'].sudo().search(
                [('channel_id', '=', rec.course_id.id), ('partner_id', '=', rec.emp_onboarding_id.employee_name.user_id.partner_id.id)], limit=1)
            rec.progress = elearning_data.completion
            if elearning_data.completion == 100:
                rec.state = 'done'

class TrainingConduct(models.Model):
    _inherit = 'training.conduct'

    emp_onboarding_id = fields.Many2one('employee.orientation', string="Employee Onboarding", ondelete='cascade')

    @api.onchange('course_id')
    def onchange_course_id(self):
        if self.course_id:
            self.conduct_line_ids = False
            if not self.emp_onboarding_id:
                for course in self.env['hr.job'].search([('course_ids', '=', self.course_id.id)]):
                    for employee in self.env['hr.employee'].search([('job_id', '=', course.id)]):
                        self.conduct_line_ids.create({
                            'conduct_id': self.id,
                            'employee_id': employee.id,
                        })
            else:
                self.conduct_line_ids.create({
                            'conduct_id': self.id,
                            'employee_id': self.emp_onboarding_id.employee_name.id,
                        })
                
class OnboardingEntryChecklist(models.Model):
    _name = 'onboarding.entry.checklist'
    _description = "Onboarding Entry Checklist"

    emp_onboarding_id = fields.Many2one('employee.orientation', string="Employee Onboarding", ondelete='cascade')
    checklist_id = fields.Many2one('employee.checklists', string="Checklist")
    document_type = fields.Selection([('entry', 'Entry Process'),
                                      ('exit', 'Exit Process')], string='Checklist Type')
    activity_type = fields.Selection([('to_do', 'To Do'),
                                      ('upload_document', 'Upload Document')], string='Activity Type')
    responsible_user_id = fields.Many2one('res.users', string="Responsible User")
    attachment = fields.Binary('Attachment')
    attachment_name = fields.Char('Attachment Name')
    feedback = fields.Text('Feedback')
    state = fields.Selection([('not_completed', 'Not Completed'),
                              ('completed', 'Completed')], default='not_completed', string='Status')

    @api.onchange('attachment')
    def onchange_attachment(self):
        for rec in self:
            if rec.attachment:
                rec.state = 'completed'
            else:
                rec.state = 'not_completed'
    
    def action_done(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'onboarding.entry.checklist.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Mark Done",
            'target': 'new',
            'context':{'default_onboard_entry_checklist_id':self.id},
        }

class OnboardingScoringProgress(models.Model):
    _name = 'onboarding.scoring.progress'
    _description = "Onboarding Scoring Progress"

    emp_onboarding_id = fields.Many2one('employee.orientation', string="Employee Onboarding", ondelete='cascade')
    onboarding_component = fields.Char('Onboarding Component')
    onboarding_weightage = fields.Float('weightage')