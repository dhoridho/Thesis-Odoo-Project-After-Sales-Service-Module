from odoo import fields, models, api


class blacklistWizard(models.TransientModel):
    _name = 'blacklist.wizard'

    blacklist_id = fields.Many2one('hr.applicant.blacklist.reason')
    description  = fields.Text()
    applicant_id = fields.Many2one('hr.applicant')

    def submit(self):
        if self.applicant_id:
            blacklist_reason_description = self.env['hr.applicant.blacklist.reason.description'].create({'blacklist_reason_id':self.blacklist_id.id,'description':self.description})
            self.applicant_id.is_hide_blacklist =True
            self.applicant_id.is_hide_remove_blacklist =False
            self.applicant_id.is_blacklist = True
            self.applicant_id.blacklist_reason_description_id = blacklist_reason_description.id
