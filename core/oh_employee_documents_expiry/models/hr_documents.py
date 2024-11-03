from odoo import models, fields,api
from lxml import etree

class HrDocument(models.Model):
    _name = 'hr.document'
    _description = 'Documents Template '

    name = fields.Char(string='Document Name', required=True, copy=False, help='You can give your'
                                                                               'Document name here.')
    note = fields.Text(string='Note', copy=False, help="Note")
    attach_id = fields.Many2many('ir.attachment', 'attach_rel', 'doc_id', 'attach_id3', string="Attachment",
                                 help='You can attach the copy of your document', copy=False)
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrDocument, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        
  
        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager')  or self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager') :
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

