from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from lxml import etree


class HRJob(models.Model):
    _inherit = 'hr.job'

    competencies_detail_ids = fields.One2many('job.competencies.detail', 'job_id', string="Competencies Detail")
    performance_all_review_id = fields.Many2one('performance.all.reviews', string="All Reviews")
    task_challenge_id = fields.Many2one('hr.task.challenge', string="Task/Challenges")
    performance_type = fields.Selection([('kpi', 'KPI'), ('okr', 'OKR')], default='kpi', string="Performance Type")
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HRJob, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.onchange('comp_template_id')
    def onchange_comp_template_id(self):
        for rec in self:
            if rec.comp_template_id:
                if rec.competencies_detail_ids:
                    remove = []
                    for line in rec.competencies_detail_ids:
                        remove.append((2, line.id))
                    rec.competencies_detail_ids = remove
                value = []
                if rec.comp_template_id.competencies_ids:
                    for line in rec.comp_template_id.competencies_ids:
                        value.append((0, 0, {'job_id':rec.id,'key_competencies_id':line.id,'name': line.name.id}))
                rec.competencies_detail_ids = value
    
    @api.constrains('competencies_detail_ids')
    def _check_overtime_reason(self):
        for rec in self:
            if rec.competencies_detail_ids:
                for line in rec.competencies_detail_ids:
                    if line.is_competency_gap and line.minimum_gap == 0:
                        raise ValidationError(_("""You must filled Minimum Gap."""))

    @api.onchange('performance_type')
    def onchange_performance_type(self):
        for rec in self:
            if rec.performance_type == "okr":
                rec.template_id = False

class HRJobCompetenciesDetail(models.Model):
    _name = 'job.competencies.detail'

    job_id = fields.Many2one('hr.job', string="Job Position")
    key_competencies_id = fields.Many2one('key.competencies', string="Competency Area")
    name = fields.Many2one('competencies.level', string="Competency Area")
    is_competency_gap = fields.Boolean('is Competency Gap')
    minimum_gap = fields.Float('Minimum Gap')

    @api.onchange('minimum_gap')
    def onchange_minimum_gap(self):
        for rec in self:
            if rec.minimum_gap > 0:
                rec.minimum_gap = 0