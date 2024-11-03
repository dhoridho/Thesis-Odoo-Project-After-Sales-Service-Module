from odoo import api, models, fields, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta 
import pytz

class DeliveryBoyLog(models.Model):
    _name = "delivery.boy.log"
    _description = 'Delivery Boy Log'
    _rec_name = "driver_id"

    driver_id = fields.Many2one("res.users",string="Driver",domain=lambda self: [('partner_id.is_driver', '=', True)])
    date = fields.Date(string="Date")
    check_in = fields.Char(string='Check In')
    check_out = fields.Char(string="Check Out")
    working_hour = fields.Char('Working Hour',readonly=False, store=True, copy=False)
    login = fields.Char(related='driver_id.login')
    country_id = fields.Many2one("res.country", related='driver_id.partner_id.country_id')
    log_fetch_ids = fields.One2many('delivery.boy.log.fetch', 'driver_log_id', string='log', compute='compute_log_fetch_ids')

    state = fields.Selection([('log_in','Log In'),('log_out','Log Out')],string="State")

    def compute_log_fetch_ids(self):
        for rec in self:
            if rec.driver_id:
                fetch =  self.env['delivery.boy.log.fetch'].search([('driver_id', '=', rec.driver_id.id)])
                if fetch:
                    rec.log_fetch_ids = [(6, 0, fetch.ids)]
                else:
                    rec.log_fetch_ids = False

    @api.model
    def create(self,vals):
        res = super(DeliveryBoyLog, self).create(vals)
        delivery_boy_status = self.env['delivery.boy.status'].search([('driver_id','=',res.driver_id.id)])
        if res.state == 'log_in':
            delivery_boy_status.state = 'online'
        else:
            delivery_boy_status.state = 'offline'
        return res

    def check_in_driver(self):
        for rec in self:
            delivery_boy_log_fetch = self.env['delivery.boy.log.fetch'].search([('driver_id','=',rec.driver_id.id),('date','=', datetime.now().astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None))])
            if not delivery_boy_log_fetch:
                now = datetime.now().astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                self.env['delivery.boy.log.fetch'].create({
                    'driver_id': rec.driver_id.id,
                    'date' :now,
                    'check_in' : now.strftime("%H:%M:%S"),
                    })
                delivery_boy_status = self.env['delivery.boy.status'].search([('driver_id','=',rec.driver_id.id)])
                delivery_boy_status.state = 'online'
            else:
                pass
                # now = datetime.now().astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                # delivery_boy_log_fetch.check_in = now.strftime("%H:%M:%S")


    def check_out_driver(self):
        for rec in self:
            delivery_boy_log_fetch = self.env['delivery.boy.log.fetch'].search([('driver_id','=',rec.driver_id.id),('date','=', datetime.now().astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None))])
            if delivery_boy_log_fetch:
                date_from = datetime.now().astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                delivery_boy_log_fetch.check_out = date_from.strftime("%H:%M:%S")
                delivery_boy_status = self.env['delivery.boy.status'].search([('driver_id','=',rec.driver_id.id)])
                delivery_boy_status.state = 'offline'
                delivery_boy_log_fetch.working_hour_delivery_boy()
                

class DeliveryBoyLogFetch(models.Model):
    _name = "delivery.boy.log.fetch"
    _description = 'Delivery Boy Log Fetch'
    _rec_name = "driver_id"

    driver_log_id = fields.Many2one('delivery.boy.log')
    driver_id = fields.Many2one("res.users",string="Driver",domain=lambda self: [('partner_id.is_driver', '=', True)])
    date = fields.Date(string="Date")
    check_in = fields.Char(string="Check In")
    check_out = fields.Char(string="Check Out")
    working_hour = fields.Char('Working Hour',readonly=False, store=True, copy=False, compute='working_hour_delivery_boy')

    def working_hour_delivery_boy(self):
        for rec in self:
            if rec.check_in and rec.check_out:
                check_in_obj = datetime.strptime(rec.check_in, '%H:%M:%S')
                check_out_obj = datetime.strptime(rec.check_out, '%H:%M:%S')
                rec.working_hour = check_out_obj - check_in_obj
