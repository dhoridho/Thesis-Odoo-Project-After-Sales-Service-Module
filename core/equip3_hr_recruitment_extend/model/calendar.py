from odoo import api, fields, models


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'
    
    applicant_name = fields.Char('Applicant Name')
    
    @api.model
    def default_get(self, fields):
        attendee_ids = []
        res = super(CalendarEvent, self).default_get(fields)
        print("res")
        if 'partner_ids' in res:
            partner = res['partner_ids'][0][2]
            for data in partner:
                attendee_ids.append((0,0,{'partner_id':data}))
            res.update({'attendee_ids': attendee_ids,
                        })
            
        # partner_ids = self.env.context.get('default_partner_ids')
        # print(self.env.context.get('default_partner_ids')[0])
        # if res['partner_ids'] and not res['attendee_ids']:
        #     for data in res['partner_ids']:
        #         attendee_ids.append((0,0,{'partner_id':data.id}))
        #     res.update({'attendee_ids': attendee_ids,
        #                 })
        return res
    
    
    
    @api.model
    def create(self, vals_list):
        res =  super(CalendarEvent,self).create(vals_list)     
        if res.attendee_ids:
            # res.action_sendmail()
            mail =  self.env['mail.mail'].search([('model','=',res._name),('res_id','=',res.id)])
            if mail:
                mail.send()
        return res