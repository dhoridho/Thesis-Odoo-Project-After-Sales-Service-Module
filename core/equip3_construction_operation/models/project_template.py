from email.policy import default
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError, _logger
from lxml import etree


class ProjectTemplate(models.Model):
    _name = 'templates.project'
    _description = 'Project Template'

    name = fields.Char(string='Project Type', required=True)
    project_template_line = fields.One2many('templates.project.line', 'project_template_id', string='Project Template')
    predecessor_template_line = fields.One2many('templates.project.predecessor', 'project_template_id', string='Predecessor Template')
    successor_template_line = fields.One2many('templates.project.successor', 'project_template_id', string='Successor Template', readonly=True)
    allowed_job_order_templates = fields.Many2many('templates.job.order', string='Allowed Job Order Templates')
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectTemplate, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    

    @api.model
    def create(self, vals):
        res = super(ProjectTemplate, self).create(vals)
        if res.predecessor_template_line:
            for rec in res.predecessor_template_line:
                res.successor_template_line = [(0, 0, {
                    'project_template_id': self.id,
                    'predecessor_task_id': rec.predecessor_task_id.id,
                    'successor_task_id': rec.successor_task_id.id,
                    'lag' : rec.lag,
                    'type' : rec.type,
                    'lag_type' : rec.lag_type,
                })]
        return res
    
    def write(self, vals):
        res = super(ProjectTemplate, self).write(vals)

        exist_predecessor = list()
        for rec in self.predecessor_template_line:
            exist_predecessor.append(rec)

        if 'predecessor_template_line' in vals:
            for i in range(len(vals['predecessor_template_line'])):
                if vals['predecessor_template_line'][i][2] != False:
                    if 'predecessor_task_id' in vals['predecessor_template_line'][i][2] and 'successor_task_id' in vals['predecessor_template_line'][i][2]:
                        self.successor_template_line = [(0, 0, {
                            'project_template_id': self.id,
                            'predecessor_task_id': vals['predecessor_template_line'][i][2]['predecessor_task_id'],
                            'successor_task_id': vals['predecessor_template_line'][i][2]['successor_task_id'],
                            'lag' : vals['predecessor_template_line'][i][2]['lag'],
                            'type' : vals['predecessor_template_line'][i][2]['type'],
                            'lag_type' : vals['predecessor_template_line'][i][2]['lag_type'],
                        })]
                    else:
                        successor = self.env['templates.project.successor'].search([('predecessor_task_id', '=', exist_predecessor[i].predecessor_task_id.id), 
                        ('successor_task_id', '=', exist_predecessor[i].successor_task_id.id)], limit=1)
                        lag, type, lag_type = None, None, None
                        if 'lag' in vals['predecessor_template_line'][i][2]:
                            lag = vals['predecessor_template_line'][i][2]['lag']
                        else:
                            lag = exist_predecessor[i].lag
                        if 'type' in vals['predecessor_template_line'][i][2]:
                            type = vals['predecessor_template_line'][i][2]['type']
                        else:
                            type = exist_predecessor[i].type
                        if 'lag_type' in vals['predecessor_template_line'][i][2]:
                            lag_type = vals['predecessor_template_line'][i][2]['lag_type']
                        else:
                            lag_type = exist_predecessor[i].lag_type

                        successor.write({
                            'lag': lag,
                            'type': type,
                            'lag_type': lag_type,
                            })
        return res

    @api.constrains('project_template_line')
    def onchange_stage_weightage(self):
        for res in self:
            if res.project_template_line:
                stage_full = sum(res.project_template_line.mapped('stage_weightage'))
                if stage_full > 100:
                    raise ValidationError(_("The total of stage weightage is more than 100%.\nPlease, re-set the weightage of each stage."))
                elif stage_full < 100:
                    raise ValidationError(_("The total of stage weightage is less than 100%.\nPlease, re-set the weightage of each stage?"))

    @api.constrains('project_template_line')
    def _check_job_order_template(self):
        for res in self:
            if res.project_template_line:
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


class ProjectTemplateLine(models.Model):
    _name = 'templates.project.line'
    _description = 'Project Template Lines'
    _order = 'sequence'

    sequence = fields.Integer(string='Sequence', default = 0)
    sr_no = fields.Integer(string='Sequence', compute='_compute_sequence_ref')
    name = fields.Char(string='Stage Name', required=True)
    stage_weightage = fields.Float(string='Stage Weightage (%)', default=0, required=True)
    job_order_template_id = fields.Many2many('templates.job.order', string='Job Order Template')
    project_template_id = fields.Many2one('templates.project', string='Project Template')

    @api.depends('project_template_id.project_template_line', 'project_template_id.project_template_line.sequence')
    def _compute_sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_template_id.project_template_line:
                no += 1
                l.sr_no = no


class ProjectTemplatePredecessor(models.Model):
    _name = 'templates.project.predecessor'
    _description = 'Predecessor'

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
                                                      ('day', 'Day'),], required=True)
    project_template_id = fields.Many2one('templates.project', string='Project Template')
    sr_no = fields.Integer(string='No.', compute='_compute_sequence_ref')

    @api.model
    def unlink(self):
        for rec in self:
            successor = self.env['templates.project.successor'].search([('predecessor_task_id', '=', rec.predecessor_task_id.id), 
            ('successor_task_id', '=', rec.successor_task_id.id), ('lag', '=', rec.lag), ('lag_type', '=', rec.lag_type), ('type', '=', rec.type)], limit=1)
            successor.unlink()
        return super(ProjectTemplatePredecessor, self).unlink()

    @api.depends('project_template_id.predecessor_template_line', 'project_template_id.predecessor_template_line.sequence')
    def _compute_sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.project_template_id.predecessor_template_line:
                no += 1
                l.sr_no = no


class ProjectTemplatePredecessorInherit(models.Model):
    _inherit = 'templates.project.predecessor'

    lag_type = fields.Selection(string='Lag Type', selection=[('minute', 'Minute'),
                                                              ('hour', 'Hour'),
                                                              ('day', 'Day'), ])


class ProjectTemplateSuccessor(models.Model):
    _name = 'templates.project.successor'
    _description = 'Successor'

    predecessor_task_id = fields.Many2one('templates.job.order', string='Predecessor')
    successor_task_id = fields.Many2one('templates.job.order', string='Successor')
    type = fields.Selection(string='Type', selection=[('FS', 'Finish to Start'), 
                                                      ('SS', 'Start to Start'),
                                                      ('FF', 'Finish to Finish'),
                                                      ('SF', 'Start to Finish'),])
    lag = fields.Integer(string='Lag', default=0)
    lag_type = fields.Selection(string='Lag Type', selection=[('minute', 'Minute'), 
                                                      ('hour', 'Hour'),
                                                      ('day', 'Day'),])
    project_template_id = fields.Many2one('templates.project', string='Project Template')

