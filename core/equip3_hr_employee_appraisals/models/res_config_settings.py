from odoo import api, fields, models


class EmployeeAppraisalsResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    appraisal_type_approval = fields.Selection(
        [('employee_hierarchy', 'By Employee Hierarchy'), ('approval_matrix', 'By Approval Matrix')], default='employee_hierarchy',
        config_parameter='equip3_hr_employee_appraisals.appraisal_type_approval')
    appraisal_level = fields.Integer(config_parameter='equip3_hr_employee_appraisals.appraisal_level', default=1)
    send_by_wa = fields.Boolean(config_parameter='equip3_hr_employee_appraisals.send_by_wa')
    send_by_email = fields.Boolean(config_parameter='equip3_hr_employee_appraisals.send_by_email', default=True)

    @api.onchange("appraisal_level")
    def _onchange_appraisal_level(self):
        if self.appraisal_level < 1:
            self.appraisal_level = 1
