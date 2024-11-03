from odoo import api, fields, models, _

class SchoolResUsers(models.Model):
    _inherit = 'res.users'

    related_student_id = fields.Many2one('student.student', string='Related Student')
    school_ids = fields.Many2many(
        comodel_name="school.school", string="Allowed School",
    )
    branch_id = fields.Many2one('res.branch', default=False)
    branch_ids = fields.Many2many('res.branch', default=False)

    @api.model
    def default_get(self, field_list):
        defaults = super(SchoolResUsers, self).default_get(field_list)
        defaults['branch_id'] = False
        defaults['branch_ids'] = False
        return defaults
    
    @api.onchange('company_id', 'company_ids')
    def _onchange_companies(self):
        self.branch_id = False  