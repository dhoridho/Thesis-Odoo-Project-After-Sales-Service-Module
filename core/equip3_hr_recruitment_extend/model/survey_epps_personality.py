from odoo import models,api,_,fields
from lxml import etree


class equip3SurveyEppsPersonality(models.Model):
    _name = 'survey.epps_personality'
    
    sequence = fields.Integer()
    code = fields.Char()
    personality = fields.Char()
    description = fields.Text()
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(equip3SurveyEppsPersonality, self).fields_view_get(
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