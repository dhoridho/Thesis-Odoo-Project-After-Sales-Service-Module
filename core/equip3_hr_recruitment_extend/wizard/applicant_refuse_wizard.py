from odoo import api, fields, models


class ApplicantGetRefuseReasonInherit(models.TransientModel):
    _inherit = 'applicant.get.refuse.reason'
    _description = 'Get Refuse Reason'



    def action_refuse_reason_apply(self):
        res = super(ApplicantGetRefuseReasonInherit,self).action_refuse_reason_apply()
        for data in self.applicant_ids:
            data.send_refuse_mail()
        return res