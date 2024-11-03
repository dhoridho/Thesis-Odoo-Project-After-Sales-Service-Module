from email.policy import default
from odoo import api, fields, models, _
from lxml import etree

class HrCompanyDocument(models.Model):
    _name = 'hr.company.document'
    _description = 'Hr Company Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Document Number')
    title = fields.Char('Title', required=True)
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted')],
                             string='Status', default='draft',
                             tracking=True)
    revision = fields.Char('Revision Number')
    general_document = fields.Boolean('General Document', default=True)
    document_type = fields.Selection(
        [('employee', 'By Employee'), ('job_position', 'By Job Position'), ('department', 'By Department')])
    description = fields.Text(string='Description')
    start_date = fields.Date(string='Effective Date', default=fields.Date.today(), required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employee')
    job_position_ids = fields.Many2many('hr.job', string='Job Position')
    department_ids = fields.Many2many('hr.department', string='Department')
    attachment_ids = fields.One2many('hr.company.document.attachment', 'document_id')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, readonly=True)

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('hr.company.document')
        vals.update({'name': sequence})
        return super(HrCompanyDocument, self).create(vals)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrCompanyDocument, self).fields_view_get(
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
    
    

    def submit(self):
        self.state = 'submitted'


class HrCompanyDocumentAttachment(models.Model):
    _name = 'hr.company.document.attachment'

    document_id = fields.Many2one('hr.company.document', string='Company Document')
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string="Attachment Name")