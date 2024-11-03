from odoo import api, models, fields
from datetime import datetime


class Equip3HrCareerTransitionGeneralInheritHrContract(models.Model):
    _inherit = "hr.contract"

    career_transition_id = fields.Many2one("career.transition.general")

    @api.model
    def create(self, vals_list):
        res = super(Equip3HrCareerTransitionGeneralInheritHrContract, self).create(
            vals_list
        )
        if res.career_transition_id:
            res.career_transition_id.is_hide_renew = True
        return res
