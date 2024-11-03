from odoo import models,api
from lxml import etree





class HashmicroMailActivityType(models.Model):
    _inherit = 'mail.activity.type'
    
    
    # @api.model
    # def fields_view_get(self, view_id=None, view_type=None,
    #                     toolbar=False, submenu=False):
    #     res = super(HashmicroMailActivityType, self).fields_view_get(
    #         view_id=view_id, view_type=view_type)
    #     if  not self.env.user.has_group('equip3_hr_accessright_settings.equip3_group_hr_recruitment_manager'):
    #         root = etree.fromstring(res['arch'])
    #         root.set('create', 'false')
    #         root.set('edit', 'false')
    #         root.set('delete', 'false')
    #         res['arch'] = etree.tostring(root)
    #     return res