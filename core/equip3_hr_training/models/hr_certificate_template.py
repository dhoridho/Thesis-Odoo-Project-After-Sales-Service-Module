from odoo import api, fields, models, _


class HRCertificateTemplate(models.Model):
    _name = 'hr.certificate.template'
    _description = 'Certificate Template'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    certificate_content = fields.Html()
    certificate_template_variables_ids = fields.One2many('hr.certificate.template.variables', 'certificate_template_id')

    @api.onchange('name')
    def _onchange_create_line_item(self):
        for rec in self:
            if not rec.certificate_template_variables_ids:
                data = [(0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(name)", 'description': "Training Conduct Name"}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(course_id)", 'description': "Training Courses"}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(trainer_type)", 'description': 'Trainer type'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(employee_ids)", 'description': 'Trainer'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(estimated_cost)", 'description': 'Estimated Cost'}),

                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(start_date)", 'description': 'Date Start'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(end_date)", 'description': 'Date Completed'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(minimal_score)", 'description': 'Minimum Score'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(created_date)", 'description': 'Created Date'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(created_by)", 'description': 'Created By'}),

                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(employee_id)", 'description': 'Employee'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(attended)", 'description': 'Attended'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(remarks)", 'description': 'Remarks'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(attachment)", 'description': 'Attachment'}),

                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(pre_test)", 'description': 'Pre Test'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(post_test)", 'description': 'Post Test'}),
                        (0, 0, {'certificate_template_id': rec.id, 'variable_name': f"$(status)", 'description': 'Status'}),
                        ]
                rec.certificate_template_variables_ids = data

class HRCertificateTemplateVariables(models.Model):

    _name = 'hr.certificate.template.variables'

    certificate_template_id = fields.Many2one('hr.certificate.template')
    variable_name = fields.Char(readonly=True)
    description = fields.Char(readonly=True)

