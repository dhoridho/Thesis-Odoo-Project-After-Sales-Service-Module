from odoo import api, fields, models, _
from lxml import etree

class HrLeaveStructure(models.Model):
    _name = 'hr.leave.structure'
    _description = "Hr Leave Structure"
    _inherit = ['mail.thread']

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    name = fields.Char('Name', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    leaves_ids = fields.Many2many('hr.leave.type', string='Leave Types', copy=True, domain=_multi_company_domain)
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrLeaveStructure, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrLeaveStructure, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrLeaveStructure, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    parent_leave_id = fields.Many2one('hr.leave.type', string='Leave Type', index=True)
    child_leaves_ids = fields.One2many('hr.leave.type', 'parent_leave_id', string='Leave Types', copy=True)
