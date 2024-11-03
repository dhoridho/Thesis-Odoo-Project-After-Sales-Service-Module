# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class OrientationForceComplete(models.TransientModel):
    _inherit = 'orientation.force.complete'

    def force_complete(self):
        res = super(OrientationForceComplete, self).force_complete()
        checklist_line = self.orientation_id.checklist_line_ids.filtered(lambda r: r.activity_type == 'upload_document' and r.attachment)
        if checklist_line:
            number = 1
            for rec in checklist_line:
                doc_number = self.orientation_id.name + "/" + str(number)
                binary = self.env["ir.attachment"].sudo().search([("res_model", "=", "onboarding.entry.checklist"),("res_id", "=", rec.id),("res_field", "=", "attachment")],limit=1)
                if binary:
                    self.env['hr.employee.document'].create({
                        'onboarding_id': self.orientation_id.id,
                        'name': doc_number,
                        'checklist_document_id': rec.checklist_id.id,
                        'employee_ref': self.orientation_id.employee_name.id,
                        'issue_date': self.orientation_id.end_date_onboarding,
                        'doc_attachment_id': [(4, file.id) for file in binary],
                    })
                    number += 1
        return res



