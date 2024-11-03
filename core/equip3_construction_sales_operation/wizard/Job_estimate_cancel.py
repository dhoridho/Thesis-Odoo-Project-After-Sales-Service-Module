from odoo import _, api, fields, models


class JobEstimateCancel(models.TransientModel):
    _name = 'job.estimate.cancel.const'
    _description = 'BOQ Cancel'

    txt = fields.Text(string="Information",default="Quotation for this BOQ has been created. Do you want to cancel this BOQ and quotation?")

    def action_confirm(self):
        job_id = self.env['job.estimate'].browse([self._context.get('active_id')])
        sale_ids = job_id.quotation_id
        job_id.write({'state':'cancel',
                      'state_new':'cancel',
                      'sale_state':'draft',
                      'is_cancelled': True
                    })
        for res in sale_ids:
            res.write({'state': 'cancel',
                       'state_1': 'cancel',
                       'sale_state': 'cancel'
                      })
    
            
