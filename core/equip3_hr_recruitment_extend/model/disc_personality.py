from odoo import fields,models,api
from lxml import etree

class DiscPersonalityInherit(models.Model):
    _inherit = 'disc.personality.root'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(DiscPersonalityInherit, self).fields_view_get(
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




class DiscPersonalityLineInherit(models.Model):
    _inherit = 'disc.personality.line'
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=True, submenu=True):
        res = super(DiscPersonalityLineInherit, self).fields_view_get(
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








