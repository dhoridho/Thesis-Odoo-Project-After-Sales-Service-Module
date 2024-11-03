from odoo import _, api, fields, models
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from lxml import etree

class EmployeeGrade(models.Model):
    _name = 'employee.grade'
    _description = 'Employee Grade'
    _inherit = ['mail.thread']

    name = fields.Char(string="Grade", tracking=True)
    description = fields.Text("Description", tracking=True)
    created_by = fields.Many2one('res.users', "Created By", default=lambda self: self.env.user)
    created_date = fields.Date("Created On", default=fields.Date.today())
    minimum_sal = fields.Float("Minimum salary", tracking=True)
    maximum_sal = fields.Float("Maximum salary", tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    job_classification_ids = fields.Many2many('employee.job.classification', string="Job Classification")

    _sql_constraints = [('name_unique', 'unique(name)', 'Grade must be unique.')]

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeGrade, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeGrade, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.constrains('minimum_sal', 'maximum_sal')
    def _check_salary(self):
        for rec in self:
            if rec.minimum_sal >= rec.maximum_sal:
                raise ValidationError(_('Minimum salary cannot be greater than maximum salary'))


    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(EmployeeGrade, self).fields_view_get(
            view_id=view_id, view_type=view_type)

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