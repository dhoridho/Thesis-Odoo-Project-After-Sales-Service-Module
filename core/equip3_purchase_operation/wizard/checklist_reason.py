
from ssl import DefaultVerifyPaths
from odoo import _, api, fields, models
import pytz
from pytz import timezone, UTC
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT   


class ChecklistReason(models.TransientModel):
    _name = "checklist.reason"
    _description = "Checklist Reason"

    reason = fields.Text(string="Reason", required=True)
    
    def action_reject(self):
        context = dict(self.env.context) or {}
        purchase_custom_checklist_line_id = self.env['purchase.custom.checklist.line'].browse([self._context.get('active_id')])
        name = "" if purchase_custom_checklist_line_id.state2 == "New" else purchase_custom_checklist_line_id.state2
        utc_datetime = datetime.now()
        local_timezone = pytz.timezone(self.env.user.tz)
        local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
        local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if name != '':
            name += "\n Cancelled - %s - %s" % (self.env.user.name, local_datetime)
        else:
            name += "Cancelled - %s - %s" % (self.env.user.name, local_datetime)
        purchase_custom_checklist_line_id.write({'state2': name, 'feedback': self.reason, 'state': 'cancelled'})
