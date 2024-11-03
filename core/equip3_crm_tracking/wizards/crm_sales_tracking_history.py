import pytz
from datetime import datetime
from odoo import models, fields, api, tools, _
import base64
import requests
from odoo.exceptions import ValidationError


class CRMSalesTrackingHistory(models.Model):
    _name = 'crm.sales.tracking.history'
    _description = 'CRM Salesperson Tracking'

    @api.onchange('sales_ids')
    def _check_salespersons(self):
        if len(self.sales_ids) > 7:
            raise ValidationError("Maximum selecting 7 salesperson")

    @api.onchange('sales_ids', 'date')
    def _compute_histories(self):
        markerColors = [
            "http://maps.google.com/mapfiles/ms/icons/red-dot.png",
            "http://maps.google.com/mapfiles/ms/icons/green-dot.png",
            "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
            "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png",
            "http://maps.google.com/mapfiles/ms/icons/pink-dot.png",
            "http://maps.google.com/mapfiles/ms/icons/orange-dot.png",
            "http://maps.google.com/mapfiles/ms/icons/purple-dot.png",
        ]
        self.history_table_ids = False
        tracking_history = self.env['crm.salesperson.tracking']
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
        used_marker = []
        for record in self.sales_ids:
                for rec in markerColors:
                    if rec not in used_marker:
                        used_marker.append(rec)
                        marker = base64.b64encode(requests.get(rec).content)
                        break
                history_ids = tracking_history.search([
                    ('sales_person', '=', record._origin.id)
                ]).filtered(lambda h: h.current_datetime.date() == self.date)
                if history_ids:
                    history_data = '<br><br>'.join([
                        '%s at <b>%s</b>' % (
                            pytz.utc.localize(h.current_datetime).astimezone(user_tz).strftime('%H:%M:%S'),
                            h.location_name
                        ) for h in history_ids
                    ])
                    self.history_table_ids = [(0, 0, {'name': record.name, 'history_data': history_data, 'marker': marker})]

    name = fields.Char('name',compute='_get_name')
    def _get_name(self):
        self.name = self.id    

    sales_ids = fields.Many2many('res.users', string='Salesperson')
    date = fields.Date(string='Date')

    history_table_ids = fields.One2many('salesperson.tracking.history', 'tracking_history_id', string="History")

    # for reporting purposes
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def action_view_crm_sales_tracking(self):
        record_id = record_id = self.env['crm.sales.tracking.history'].search([], limit=1)
        if not record_id:
            record_id = self.env['crm.sales.tracking.history'].create({})

        record_id.write({
            'sales_ids': False,
            'date': False
        })
        record_id._compute_histories()

        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.sales.tracking.history',
            'view_mode': 'form',
            'target': 'current',
            'res_id': record_id.id,
            'view_id': self.env.ref('equip3_crm_tracking.view_crm_sales_tracking_history_form').id,
            'context': {'form_view_initial_mode': 'edit'}
        }

    def action_print_report(self):
        self.history_table_ids = False
        self._compute_histories()
        return self.env.ref('equip3_crm_tracking.action_print_crm_sales_tracking_history_report').report_action(self)

    def get_history_data(self):
        data = "<html>"
        for record in self.sales_ids:
            tracking_history = self.env['crm.salesperson.tracking'].search([
                    ('sales_person', '=', record._origin.id)
                ]).filtered(lambda h: h.current_datetime.date() == self.date)
            if len(tracking_history) != 0:
                data = data + "<p style='font-size:16px;'>Salesperson: " + record.name + "</p> <div style='width:100%;'> <table style='width:100%; border:1px solid #c1c1c1; border-collapse: collapse;' class='table table-bordered'> <tr style='background-color:black; color:white; text-align:center;'> <td style='width:50%;font-size:16px;'>Time</td> <td style='font-size:16px;'>Location</td> </tr>"
                for rec in tracking_history:
                    data = data + "<tr style='text-align:center;'> <td style='border:1px solid #c1c1c1; width:50%; font-size:16px;'>" + str(rec.current_datetime) + "</td> <td style='border:1px solid #c1c1c1; font-size:16px;'>" + str(rec.location_name) + "</td> </tr>"
                data = data + "</table> </div>"
        data = data + "</html>"

        return data

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False


class CRMSalesTrackingHistoryTable(models.Model):
    _name = 'salesperson.tracking.history'
    _description = 'CRM Salesperson Tracking History'

    name = fields.Char()
    marker = fields.Binary()
    history_data = fields.Html()
    tracking_history_id = fields.Many2one('crm.sales.tracking.history',string="Salesperson Tracking History ref")