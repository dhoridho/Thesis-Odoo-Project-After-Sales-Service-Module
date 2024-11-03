from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo import tools
from datetime import datetime, timedelta, date


class ProjectTemplateConfirmationWizard(models.TransientModel):
    _name = 'project.template.confirmation.wizard'
    _description = 'Project Template Confirmation'

    template_id = fields.Many2one('templates.project', string='Project Type')
    project_id = fields.Many2one('project.project', string="Project")
    sale_order_id = fields.Many2one('sale.order.const', string="Contract")
    project_template_line = fields.One2many('project.template.line.wizard', 'project_template_id', string='Project Template')
    predecessor_template_line = fields.One2many('project.template.predecessor.wizard', 'project_template_id', string='Predecessor Template')
    successor_template_line = fields.One2many('project.template.successor.wizard', 'project_template_id', string='Successor Template')
    total_weightage = fields.Float(string="Total Weightage", compute="_total_weightage")
    allowed_job_order_templates = fields.Many2many('templates.job.order', string='Allowed Job Order Templates')

    @api.depends('project_template_line.stage_weightage')
    def _total_weightage(self):
        total = 0
        for res in self:
            total = sum(res.project_template_line.mapped('stage_weightage'))
            res.total_weightage = total
        return total

    def action_confirm(self):
        for res in self:
            if not res.project_template_line:
                raise ValidationError(_('Please, input the stage for this contract project.'))

            elif res.total_weightage < 100:
                    raise ValidationError(_('The total of stage weightage is less than 100%. \nPlease, re-input the weightage of each stage.'))

            elif res.total_weightage > 100:
                raise ValidationError(_('The total of stage weightage is more than 100%. \nPlease, re-set the weightage of each stage.'))
            
            else:

                if res.allowed_job_order_templates:
                    tmp = []
                    for ptl in res.project_template_line:
                        if ptl.job_order_template_id:
                            tmp.extend(ptl.job_order_template_id.mapped('name'))
                    exist = set()
                    duplicated = []
                    for j in tmp:
                        if j in exist:
                            duplicated.append(j)
                        exist.add(j)
                    msg = ", ".join(duplicated)
                    if msg:
                        raise ValidationError(_("Job Order Template: %s can't duplicated in Project Template Lines") % msg)
                
                    for proj in res.project_template_line:
                        if proj.job_order_template_id:
                            percentage_sum = sum(proj.job_order_template_id.mapped('task_weightage'))
                            if percentage_sum > 100:
                                raise ValidationError(_("The total of job order weightage in stage %s is more than 100%.\
                                                        \nPlease, re-set the job order in %s stage.") % (proj.name, proj.name))
            
                

                if res.project_template_line:
                    for project in res.project_template_line:
                        name = project.name
                        stages = res.env['project.task.type'].search([('name', '=', name)])
                        if len(stages) == 0:
                            res.env['project.task.type'].create({'name': name})

                    res.env['project.completion.const'].create({
                        'completion_id': res.project_id.id,
                        'project_completion': 0,
                        'project_id': res.project_id.name,
                        'name': res.sale_order_id.id,
                    })

                    stage_id = res.env['project.completion.const'].search([('name', '=', res.sale_order_id.id)])
                    
                    for project in res.project_template_line:
                        name = project.name
                        stages = res.env['project.task.type'].search([('name', '=', name)])
                        if len(stages) > 0:
                            res.env['project.stage.const'].create({
                                'name': stages.id,
                                'stage_id': stage_id.id,
                                'sequence': project.sequence,
                                'stage_weightage': project.stage_weightage,
                                'stage_completion': 0,
                            })
                    
                    proj = res.project_id
                    cost_sheet = res.env['job.cost.sheet'].search([('project_id', '=', proj.id),('state', '!=', 'cancelled')],limit="1")
                    for project in res.project_template_line:
                        name = project.name
                        stages = res.env['project.task.type'].search([('name', '=', name)])
                        for job_order in project.job_order_template_id:
                            proj_stage = res.env['project.stage.const']\
                                            .search([('name', '=', stages.id), ('stage_id', '=', stage_id.id)])
                            weightage_used = 0
                            for i in self.env['project.task'].search([
                                ('is_subcon','=',False),
                                ('is_subtask','=',False),
                                ('project_id', '=', proj.id),
                                ('sale_order', '=', res.sale_order_id.id),
                                ('stage_new', '=', proj_stage.id)]):
                                weightage_used += i.work_weightage

                            res.env['project.task'].create({
                                'name': job_order.name,
                                'state': 'draft',
                                'project_id': proj.id,
                                'company_id': res.env.company.id,
                                'completion_ref': stage_id.id, 
                                'cost_sheet': cost_sheet.id,
                                'partner_id': proj.partner_id.id,
                                'sale_order': res.sale_order_id.id,
                                'project_director': proj.project_director.id,
                                'stage_new': proj_stage.id,
                                'stage_weightage': proj_stage.stage_weightage,
                                'work_weightage': job_order.task_weightage,
                                'work_weightage_remaining': 100 - weightage_used,
                                'sale_order_id': False,
                                'tag_ids': job_order.tag_ids,
                                'new_description': job_order.new_description,
                                'is_subcon': job_order.is_subcon,
                                })
                    
                if res.predecessor_template_line:
                    for template in res.predecessor_template_line:
                        pre_job_order = template.predecessor_task_id
                        suc_job_order = template.successor_task_id

                        pre_parent = self.env['project.task'].search([
                            ('name', '=', pre_job_order.name),
                            ('project_id', '=', proj.id),
                            ('sale_order', '=', res.sale_order_id.id)])

                        suc_parent = self.env['project.task'].search([
                            ('name', '=', suc_job_order.name),
                            ('project_id', '=', proj.id),
                            ('sale_order', '=', res.sale_order_id.id)])
                        
                        res.env['project.task.predecessor'].create({
                            'task_id': suc_parent.id,
                            'parent_task_id': pre_parent.id,
                            'type': template.type,
                            'lag_qty': template.lag,
                            'lag_type': template.lag_type
                        })
                        
    @api.onchange('template_id')
    def _compute_allowed_job_order_templates(self):
        for rec in self:
            rec.allowed_job_order_templates = [(6, 0, [v.id for v in rec.template_id.allowed_job_order_templates])]

    @api.onchange('template_id')
    def _compute_project_template_line(self):
        project_template_line = [(5, 0, 0)]
        for rec in self:
            for line in rec.template_id.project_template_line:
                project_template_line.append((0, 0,{
                    'sequence': line.sequence,
                    'sr_no': line.sr_no,
                    'name': line.name,
                    'stage_weightage': line.stage_weightage,
                    'job_order_template_id': [(6, 0, [v.id for v in line.job_order_template_id])],
                    'project_template_id': rec.id,
                }))
            rec.project_template_line = project_template_line

    @api.onchange('template_id')
    def _compute_predecessor_template_line(self):
        predecessor_template_line = [(5, 0, 0)]
        for rec in self:
            for line in rec.template_id.predecessor_template_line:
                predecessor_template_line.append((0, 0,{
                    'sequence': line.sequence,
                    'predecessor_task_id': line.predecessor_task_id.id,
                    'successor_task_id': line.successor_task_id.id,
                    'type': line.type,
                    'lag': line.lag,
                    'lag_type': line.lag_type,
                    'project_template_id': rec.id,
                }))
            rec.predecessor_template_line = predecessor_template_line

    @api.depends('template_id')
    def _compute_successor_template_line(self):
        successor_template_line = [(5, 0, 0)]
        for rec in self:
            for line in rec.template_id.successor_template_line:
                successor_template_line.append((0, 0,{
                    'predecessor_task_id': line.predecessor_task_id.id,
                    'successor_task_id': line.successor_task_id.id,
                    'type': line.type,
                    'lag': line.lag,
                    'lag_type': line.lag_type,
                    'project_template_id': rec.id,
                }))
            rec.successor_template_line = successor_template_line


# to store temporary project template line data
class ProjectTemplateLineWizard(models.TransientModel):
    _name = 'project.template.line.wizard'
    _description = 'Project Template Line Wizard'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default = 0)
    sr_no = fields.Integer(string='Stage Number', compute='_compute_sequence_ref')
    name = fields.Char(string='Stage Name', required=True)
    stage_weightage = fields.Float(string='Stage Weightage (%)', default=0, required=True)
    job_order_template_id = fields.Many2many('templates.job.order', string='Job Order Template')
    project_template_id = fields.Many2one('project.template.confirmation.wizard', string='Project Template')

    @api.depends('project_template_id.project_template_line', 'project_template_id.project_template_line.sequence')
    def _compute_sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_template_id.project_template_line:
                no += 1
                l.sr_no = no


# to store temporary project template predecessor data
class ProjectTemplatePredecessorWizard(models.TransientModel):
    _name = 'project.template.predecessor.wizard'
    _description = 'Predecessor Wizard'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default = 0)
    predecessor_task_id = fields.Many2one('templates.job.order', string='Predecessor', required=True)
    successor_task_id = fields.Many2one('templates.job.order', string='Successor', required=True)
    type = fields.Selection(string='Type', selection=[('FS', 'Finish to Start'), 
                                                      ('SS', 'Start to Start'),
                                                      ('FF', 'Finish to Finish'),
                                                      ('SF', 'Start to Finish'),], required=True)
    lag = fields.Integer(string='Lag', default=0)
    lag_type = fields.Selection(string='Lag Type', selection=[('minute', 'Minute'), 
                                                      ('hour', 'Hour'),
                                                      ('day', 'Day')], required=True)
    project_template_id = fields.Many2one('project.template.confirmation.wizard', string='Project Template')
    sr_no = fields.Integer(string='No.', compute='_compute_sequence_ref')

    
    @api.depends('project_template_id.predecessor_template_line', 'project_template_id.predecessor_template_line.sequence')
    def _compute_sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_template_id.predecessor_template_line:
                no += 1
                l.sr_no = no


# to store temporary project template successor data
class ProjectTemplateSuccessorWizard(models.TransientModel):
    _name = 'project.template.successor.wizard'
    _description = 'Successor Wizard'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default = 0)
    predecessor_task_id = fields.Many2one('templates.job.order', string='Predecessor', required=True)
    successor_task_id = fields.Many2one('templates.job.order', string='Successor', required=True)
    type = fields.Selection(string='Type', selection=[('FS', 'Finish to Start'),
                                                        ('SS', 'Start to Start'),   
                                                        ('FF', 'Finish to Finish'),
                                                        ('SF', 'Start to Finish'),], required=True)
    lag = fields.Integer(string='Lag', default=0)
    lag_type = fields.Selection(string='Lag Type', selection=[('minute', 'Minute'),
                                                        ('hour', 'Hour'),
                                                        ('day', 'Day')], required=True)
    project_template_id = fields.Many2one('project.template.confirmation.wizard', string='Project Template')
