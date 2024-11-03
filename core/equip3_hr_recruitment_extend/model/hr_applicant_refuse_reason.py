from odoo import models,api, fields
from lxml import etree
from odoo import exceptions






class HashmicrohrApplicantRefuseReason(models.Model):
    _inherit = 'hr.applicant.refuse.reason'

    applicant_weightage = fields.Boolean('Applicant Weightage')

    @api.model
    def create(self, vals):
        if vals.get('applicant_weightage', True):
            existing_records = self.search([('applicant_weightage', '=', True)])
            if existing_records:
                raise exceptions.Warning(
                    """'Please set only one boolean on applicant question to be true!""")
        existing_records = self.search([('applicant_weightage', '=', True)])
        if not existing_records:
            name = vals.get('name')
            if name and name == "Doesn't fit the job requirements":
                vals['applicant_weightage'] = True
        return super(HashmicrohrApplicantRefuseReason, self).create(vals)

    def write(self, vals):
        if 'applicant_weightage' in vals and vals['applicant_weightage']:
            existing_records = self.search([('applicant_weightage', '=', True), ('id', '!=', self.id)])
            if existing_records:
                raise exceptions.Warning(
                    """Please set only one boolean on applicant question to be true!""")
        return super(HashmicrohrApplicantRefuseReason, self).write(vals)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(HashmicrohrApplicantRefuseReason, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if  not self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        if view_type == 'tree':
            existing_records = self.search([('applicant_weightage', '=', True)], limit=1)
            if not existing_records:
                record = self.search([('name', '=', "Doesn't fit the job requirements")], limit=1)
                if record:
                    record.applicant_weightage = True
        return res