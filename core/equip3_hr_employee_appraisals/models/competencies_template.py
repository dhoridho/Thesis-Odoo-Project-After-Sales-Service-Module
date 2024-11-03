
from odoo import models, fields, api, _
from odoo import tools
from lxml  import etree

class CompetenciesTemplateInherit(models.Model):
    _inherit = 'competencies.template'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(CompetenciesTemplateInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)   
        elif self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)       
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res





class KeyCompetenciesAppraisal(models.Model):
    _inherit = 'key.competencies'
    name = fields.Many2one('competencies.level',string="Competency Areas")
    target_score_id = fields.Many2one('competencies.level.line',string="Score", domain="[('competencies_id','=',name)]")
    description = fields.Text()
    description_replace = fields.Text(string='Description', compute="compute_description")
    weightage = fields.Float()

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.description = self.name.description
            
    @api.depends('description')
    def compute_description(self):
        for rec in self:
            rec.description_replace = rec.description
        
class KeyPerformanceAppraisal(models.Model):
    _inherit = 'key.performance'
    name = fields.Many2one('gamification.goal.definition',string="KPI")
    description = fields.Text()
    kpi_target = fields.Float()
    weightage = fields.Float()

    @api.onchange('name')
    def onchange_name(self):
        if self.name:
            self.description = self.name.description