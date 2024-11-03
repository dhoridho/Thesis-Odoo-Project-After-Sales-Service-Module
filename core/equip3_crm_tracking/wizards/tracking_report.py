import datetime
import json
import pytz

from odoo import models, fields
from odoo.exceptions import UserError

class SalespersonTrackingReport(models.TransientModel):
    _name = 'crm.salesperson.tracking.report'
    _description = "Salesperson Tracking Report"

    sales_person = fields.Many2one('res.users', string='Sales Person', required=True)
    current_datetime = fields.Date(string="Date", required=True)

    def view_track(self):
        track_records = self.env['crm.salesperson.tracking'].search([('sales_person', '=', self.sales_person[0].id), ('current_datetime', '>=', str(self.current_datetime) + ' 00:00:00'), ('current_datetime', '<=', str(self.current_datetime) + ' 23:59:59')], order="id asc")
        if track_records:
            track_list = []
            track_lan_lng = []
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)

            for track_rec in track_records:
                lat = float(track_rec.latitude)
                lng = float(track_rec.longitude)
                maps_loc = {u'latitude': lat, u'longitude': lng, u'timestamp': track_rec.location_name}
                json_map = json.dumps(maps_loc)
                track_lan_lng.append(maps_loc)

                time_in_timezone = pytz.utc.localize(track_rec.current_datetime).astimezone(user_tz)

                vals = {
                    'time_loc_str': time_in_timezone.strftime('%H:%M:%S')+' at '+track_rec.location_name+'<br>',
                    'lat_lng': json_map,
                }
                track_list.append(vals)

            fetched_data = self.env['crm.salesperson.tracking.history'].create({'sales_person_name': self.sales_person[0].display_name,
                'history_date': str(self.current_datetime), 'track_list': track_list, 'track_lan_lng': json.dumps(track_lan_lng)
            })
            return fetched_data
        else:
            raise UserError("""No track record found""")

class SalespersonTrackingHistory(models.TransientModel):
    _name = 'crm.salesperson.tracking.history'
    _description = "Salesperson Tracking History"

    sales_person_name = fields.Char(string="Salesperson")
    history_date = fields.Char(string="Date")
    track_lan_lng = fields.Char(string="Tracking Coordinates")
    track_hist = fields.Html('Visit History')

    def create(self, vals):
        hist_html = ""
        for date_loc_obj in vals['track_list']:
            date_loc = date_loc_obj['time_loc_str']
            hist_html += date_loc + "<br>"

        return {
                'type': 'ir.actions.act_window',
                'res_model': 'crm.salesperson.tracking.history',
                'view_mode': 'form',
                'target': 'current',
                'res_id': self.id,
                'flags': {'mode': 'readonly'},
                'context': {
                    'default_sales_person_name': vals['sales_person_name'],
                    'default_history_date': vals['history_date'],
                    'default_track_hist': hist_html,
                    'default_track_lan_lng': vals['track_lan_lng'],
                }
        }