from odoo import api, fields, models
from lxml import etree


class JobOrderTemplate(models.Model):
    _name = 'templates.job.order'
    _description = 'Job Order Template'

    priority = fields.Selection(string='Priority', selection=[('0', 'Normal'), ('1', 'Important'),])
    name = fields.Char(string='Job Order Title', required=True)
    tag_id = fields.Many2one('project.tags', string='Tags')
    task_weightage = fields.Float(string='Job Order Weightage')
    description = fields.Html(string='Description')
    tag_ids = fields.Many2many('project.tags', 'tag_rel','tag_id','id_tag', string='Tags')
    is_subcon = fields.Boolean(string='Job Order Subcon')
    new_description = fields.Html(string='Description')
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(JobOrderTemplate, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res    
    
    

    
    
