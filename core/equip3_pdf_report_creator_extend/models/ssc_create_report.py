from odoo import models, api, fields, _



class SscReportCreator(models.Model):
    _inherit = 'ssc.create.report'

    
    def action_test_mail_send(self):

        res =  super(SscReportCreator, self).action_test_mail_send()
        res['name'] = self.template_id.name

        return res