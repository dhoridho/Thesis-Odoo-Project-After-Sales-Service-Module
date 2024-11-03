from odoo import _, api, fields, models
from lxml import etree

class JobClassification(models.Model):
    _name = 'employee.job.classification'
    _description = 'Job Experience Level'
    _inherit = ['mail.thread']

    name = fields.Char(string="Job Classification", tracking=True)
    description = fields.Text("Description", tracking=True)
    job_allowance = fields.Float("Job Allowance", tracking=True)
    created_by = fields.Many2one('res.users', "Created By", default=lambda self: self.env.user)
    created_date = fields.Date("Created On", default=fields.Date.today())
    company_id = fields.Many2one('res.company', string='Company', tracking=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    classify_detail_ids = fields.One2many('job.classification.detail',
                                          'job_id', "Job Classification Detail")

    _sql_constraints = [('name_unique', 'unique(name)', 'Job Classification must be unique.')]


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(JobClassification, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(JobClassification, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(JobClassification, self).fields_view_get(
            view_id=view_id, view_type=view_type)

        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
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

class JobClassificationDetail(models.Model):
    _name = 'job.classification.detail'
    _description = 'Job Classification Detail'

    @api.model
    def _experience_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    name = fields.Integer(string="Sequence", compute="fetch_sl_no")
    job_id = fields.Many2one('employee.job.classification', string="Job Classification")
    experience_ids = fields.Many2many('employee.job.experience.level', string="Experience Level", domain=_experience_domain)
    job_experience_allowance = fields.Float(string="Job Experience Allowance")
    grade_id = fields.Many2many('employee.grade', string="Employee Grade")

    def fetch_sl_no(self):
        sl = 0
        if self.ids:
            line_id = self.browse(self.ids[0])
            for line in line_id.job_id.classify_detail_ids:
                sl = sl + 1
                line.name = sl

    @api.model
    def create(self, vals):
        rec = super(JobClassificationDetail, self).create(vals)
        for grade in rec.grade_id:
            grade.write({'job_classification_ids': ([(4, rec.job_id.id)])})
        for level in rec.experience_ids:
            level.write({'classification_ids': ([(4, rec.job_id.id)])})
        return rec

    def write(self, vals):
        rec = super(JobClassificationDetail, self).write(vals)
        for detail in self:
            for grade in detail.grade_id:
                grade.write({'job_classification_ids': ([(4, detail.job_id.id)])})
            for level in detail.experience_ids:
                level.write({'classification_ids': ([(4, detail.job_id.id)])})
            # for level in self.env['job.experience.level'].search([('name', '=', detail.experience_id.name)]):
            #     level.write({'classification_id': detail.job_id.id})
        return rec
