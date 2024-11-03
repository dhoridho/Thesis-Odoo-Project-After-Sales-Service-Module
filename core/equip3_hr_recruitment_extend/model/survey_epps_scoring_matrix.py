from odoo import models,api,_,fields
from lxml import etree


class Equip3SurveyEppsScoringMatrixInherit(models.Model):
    _inherit= 'survey.epps.scoring.matrix'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(Equip3SurveyEppsScoringMatrixInherit, self).fields_view_get(
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

    
    
    
class Equip3SurveyEppsScoringMatrixLineInherit(models.Model):
    _inherit = 'survey.epps.scoring.matrix.line'
    
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(Equip3SurveyEppsScoringMatrixLineInherit, self).fields_view_get(
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
    

    