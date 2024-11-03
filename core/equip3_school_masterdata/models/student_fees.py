from odoo import _, api, fields, models


class StudentFeesStructureInherit(models.Model):
    _inherit = "student.fees.structure"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Fees Structure"
    )


class StudentFeesStructureLineInherit(models.Model):
    _inherit = "student.fees.structure.line"

    active = fields.Boolean(
        default=True, help="Activate/Deactivate Fees Head"
    )
