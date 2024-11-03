
from odoo import fields, models, api
import pytz
from pytz import timezone, UTC
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT   



class CRMCustomChecklistLine(models.Model):
    _inherit = 'purchase.custom.checklist.line'
    
    state2 = fields.Char(string="State", default="New", readonly=True)
    feedback = fields.Text(string="Feedback", readonly=True)
    
    def btn_check(self):
        res = super(CRMCustomChecklistLine, self).btn_close()
        user = self.env.user
        for record in self:
            if user.id:
                name = '' if record.state2 == "New" else record.state2
                utc_datetime = datetime.now()
                local_timezone = pytz.timezone(self.env.user.tz)
                local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if name != '':
                    name += "\n Completed - %s - %s" % (self.env.user.name, local_datetime)
                else:
                    name += "Completed - %s - %s" % (self.env.user.name, local_datetime)
            record.state2 = name
            record.state = "completed"
        return res
    
    def btn_close(self):
        res = super(CRMCustomChecklistLine, self).btn_close()
        context = dict(self.env.context) or {}
        context.update({
            'active_id': self.id, 
            'active_ids': self.ids
            })
        return {
                'type': 'ir.actions.act_window',
                'name': 'Rejected Reason',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'checklist.reason',
                'target': 'new',
                'context': context
            }
        return res