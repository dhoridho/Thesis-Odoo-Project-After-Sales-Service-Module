
from odoo import models,fields,api
from odoo.exceptions import ValidationError
from lxml import etree


class surveyDiscVariablesInherit(models.Model):
    _inherit = 'survey.disc.variables'
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(surveyDiscVariablesInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            res['arch'] = etree.tostring(root)
        elif  self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            res['arch'] = etree.tostring(root)

        return res
   



class surveyDiscVariableJobSuggestionInherit(models.Model):
    _inherit = 'survey.disc.job.suggestion'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(surveyDiscVariableJobSuggestionInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            res['arch'] = etree.tostring(root)
        elif  self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            res['arch'] = etree.tostring(root)

        return res

