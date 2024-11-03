from odoo import _, api, fields, models
from lxml import etree

class EmployeeReligion(models.Model):
    _name = 'employee.religion'
    _description = 'Employee Religion'
    _inherit = ['mail.thread']
    _order = 'name ASC'

    name = fields.Char(string='Name', tracking=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeReligion, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeReligion, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(EmployeeReligion, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
   
        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
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
