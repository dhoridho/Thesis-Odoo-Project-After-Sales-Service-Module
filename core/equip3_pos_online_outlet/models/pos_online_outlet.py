# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from pytz import timezone
from dateutil import parser

class PosOnlineOutlet(models.Model):
    _name = "pos.online.outlet"
    _description = "Pos Online Outlet"

    def _default_operational_hour_ids(self):
        values = []
        for day in ['sunday','monday','tuesday','wednesday','thursday','friday','saturday']:
            values += [(0, 0, {'day': day, 'start_time': 8.0, 'end_time': 22.0 })]
        return values

    name = fields.Char('Outlet Name', help="Outlet Name")
    state = fields.Selection([('open','Open'), ('closed', 'Closed')], string='Status', default='closed')
    close_duration = fields.Char('Close Duration')
    close_date = fields.Datetime('Close Date')
    operational_hour_ids = fields.One2many('pos.online.outlet.operational.hour', 'outlet_id', string="Operational Hours", default=_default_operational_hour_ids)
    category_ids = fields.Many2many(
        'pos.category', 
        'pos_online_outlet_pos_category_rel', 
        'pos_online_outlet_id', 
        'pos_category_id', 
        string='Categories (2)')
    currency_id = fields.Many2one('res.currency', domain="[('name','in', ['IDR','SGD'])]")
    categ_ids = fields.One2many('pos.online.outlet.categories', 'outlet_id', string='Categories')
    product_ids = fields.One2many('pos.online.outlet.products', 'outlet_id', string='Products')
    country_code = fields.Char('Country Code', default='ID')
    

    @api.model
    def create(self, values):
        res = super(PosOnlineOutlet, self).create(values)
        for outlet in res:
            outlet.update_categories_and_products()
            outlet.update_online_state()
        return res

    def write(self, vals):
        res = super(PosOnlineOutlet, self).write(vals)
        if 'state' in vals:
            for outlet in self:
                outlet.update_online_state()
        return res

    def change_online_outlet_state(self):
        values = {
            'status': 'success',
            'id': self.id,
        }
        state = self._context.get('state')
        if state in ['open', 'closed']:
            self.write({
                'state': state,
            })
        return values

    def check_outlet_status(self):
        pass

    def action_update_menu(self):
        pass

    def grabfood_auto_update_menu(self):
        pass

    def update_online_state(self):
        pass

    def format24hour(self, hours):
        td = timedelta(hours=hours)
        dt = datetime.min + td
        return "{:%H:%M}".format(dt)

    def get_outlet_selling_time(self):
        self.ensure_one()
        outlet = self
        operational_hours = outlet.operational_hour_ids
        start_time = self.format24hour(min([x.start_time for x in operational_hours]))
        end_time = self.format24hour(max([x.end_time for x in operational_hours]))
        start_date = '%s %s:00' % ( datetime.today().strftime('%Y-%m-%d'), str(start_time) )
        end_date = '%s %s:00' % ( (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d'), end_time)

        service_hours = {}
        for service in operational_hours:
            service_hours[service.day[:3]] = {
                "openPeriodType": "OpenPeriod", 
                "periods": [{ 
                    "startTime": service.start_time_24hour, "endTime": service.end_time_24hour 
                }]
            }

        return {
            "startTime": start_date,
            "endTime": end_date,
            "id": "operationalHourID-%s" % str(outlet.id),
            "name": outlet.name,
            "serviceHours": service_hours
        }

    def update_categories_and_products(self):
        self.ensure_one()
        online_outlet_obj = self.env['pos.online.outlet']
        pos_categ_obj = self.env['pos.category']
        online_outlet_categ_obj = self.env['pos.online.outlet.categories']
        online_outlet_product_obj = self.env['pos.online.outlet.products']
        values_create = []
        values_create_p = []
        all_pos_categ_ids = pos_categ_obj.search([('is_online_outlet','=',True)]).ids
        all_product_ids = self.env['product.template'].search([('is_online_outlet','=',True),('oloutlet_category_id.is_online_outlet','=',True)]).ids
        outlet_id = self.id
        for product_id in all_product_ids:
            check_exist_product = online_outlet_product_obj.search([('outlet_id','=',outlet_id),('product_tmpl_id','=',product_id)],limit=1).ids
            if check_exist_product:
                continue
            values_create_p.append({
                'outlet_id': outlet_id,
                'product_tmpl_id': product_id
            })
        if values_create_p:
            online_outlet_product_obj.create(values_create_p)

        for categ_id in all_pos_categ_ids:
            values = {
                'outlet_id': outlet_id,
                'pos_categ_id': categ_id
            }
            values_create.append(values)
        if values_create:
            online_outlet_categ_obj.create(values_create)
            
        return True


class PosOnlineOutletProductOption(models.Model):
    _name = "pos.online.outlet.product.option"
    _description = "Pos Online Outlet Product Option"
    _order = 'sequence asc'

    oloutlet_product_tmpl_id = fields.Many2one('product.template', string="Product Template")
    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    product_tmpl_ids = fields.Many2many('product.template', 'pos_online_outlet_product_option_product_template_rel', 
        'pos_online_outlet_product_option_id', 'product_template_id', 
        domain="[('type','=','product'),('available_in_pos','=',True)]",
        string='Options')
    min_selection = fields.Integer('Min Selection',  default=1,
        help='''Optional - If modifier group is optional, the value must be zero.\nMandatory - If modifier group is mandatory, the velue must be greater than or equal to 1.''')

class PosOnlineOutletCategories(models.Model):
    _name = 'pos.online.outlet.categories'
    _description = 'Pos Online Outlet Categories'
    _rec_name = 'pos_categ_id'
    _order = 'sequence asc'

    outlet_id = fields.Many2one('pos.online.outlet', string='Outlet')
    sequence = fields.Integer('Sequence')
    pos_categ_id = fields.Many2one('pos.category', string='PoS Product Categories')
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    available_in_grabfood = fields.Boolean('Available in Grabfood', default=True)
    available_in_gofood = fields.Boolean('Available in GoFood', default=True)
    line_product_ids = fields.One2many('pos.online.outlet.products', string='Products', compute='_compute_line_product_ids')

    @api.depends('pos_categ_id','pos_categ_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.pos_categ_id and rec.pos_categ_id.name or 'None'

    def _compute_line_product_ids(self):
        for rec in self:
            domain = [('outlet_id','=', rec.outlet_id.id), ('product_tmpl_id.oloutlet_category_id','=', rec.pos_categ_id.id)]
            rec.line_product_ids = self.env['pos.online.outlet.products'].search(domain)

class PosOnlineOutletProducts(models.Model):
    _name = 'pos.online.outlet.products'
    _description = 'Pos Online Outlet Products'
    _order = 'sequence asc'
    
    outlet_id = fields.Many2one('pos.online.outlet', string='Outlet')
    sequence = fields.Integer('Sequence')
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    pos_categ_id = fields.Many2one('pos.category', related='product_tmpl_id.oloutlet_category_id', string='Category', store=True)
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    is_available = fields.Boolean('Available', default=True)

    @api.depends('pos_categ_id','pos_categ_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = rec.pos_categ_id and rec.pos_categ_id.name or 'None'



class PosOnlineOutletCampaign(models.Model):
    _name = 'pos.online.outlet.campaign'

    name = fields.Char('Name')
    external_id = fields.Char('External ID')
    campaign_type = fields.Selection([], string='Campaign Type')
    outlet_id = fields.Many2one('pos.online.outlet', string='Outlet')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    start_time = fields.Float('Start Time', default=8)
    end_time = fields.Float('End Time', default=22)
    is_sunday = fields.Boolean('Sunday', default=True)
    is_monday = fields.Boolean('Monday', default=True)
    is_tuesday = fields.Boolean('Tuesday', default=True)
    is_wednesday = fields.Boolean('Wednesday', default=True)
    is_thursday = fields.Boolean('Thursday', default=True)
    is_friday = fields.Boolean('Friday', default=True)
    is_saturday = fields.Boolean('Saturday', default=True)
    discount_value = fields.Integer('Value')




class PosOnlineOutletOperationalHour(models.Model):
    _name = "pos.online.outlet.operational.hour"
    _description = "Pos Online Outlet Operational Hour"
    
    outlet_id = fields.Many2one('pos.online.outlet', string='Outlet')
    day = fields.Selection([
        ('sunday', 'Sunday'),
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ], string="Day Open", required=True)
    start_time = fields.Float('Start Time')
    end_time = fields.Float('End Time')
    start_time_24hour = fields.Char('Start Time (24hour format)', compute='_compute_time_24hour')
    end_time_24hour = fields.Char('End Time (24hour format)', compute='_compute_time_24hour')


    def _compute_time_24hour(self):
        Outlet = self.env['pos.online.outlet']
        for rec in self:
            rec.start_time_24hour = Outlet.format24hour(rec.start_time)
            rec.end_time_24hour = Outlet.format24hour(rec.end_time)

    def get_date_in_utc(self, hour):
        _timezone = self.env['ir.config_parameter'].sudo().get_param('base_setup.oloutlet_timezone') or 'Asia/Jakarta'
        formatdate = '%Y-%m-%d %H:%M:%S'
        today_date = datetime.now().strftime('%Y-%m-%d')
        date = datetime.strptime(f'{today_date} {hour}:00', formatdate).replace(tzinfo=timezone(_timezone))
        date_in_utc = datetime.strptime(date.astimezone(timezone('utc')).strftime(formatdate), formatdate)
        return date_in_utc


class PosOnlineOutletOrder(models.Model):
    _name = "pos.online.outlet.order"
    _description = "Pos Online Outlet Order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'order_number'
    _order = 'create_date desc'

    online_outlet_id = fields.Many2one('pos.online.outlet', 'Outlet')
    order_number = fields.Char('Order Number')
    order_from = fields.Selection([('grabfood','GrabFood'), ('gofood','GoFood')], string='Order From')
    order_type = fields.Selection([
        ('self-pickup','Self-pickup'), #Pickup/TakeAway/Self-collection
        ('grab-delivery','Grab delivery'), 
        ('outlet-delivery','Outlet delivery'), 
        ('dine-in','Dine-in'), 
    ], 
    string='Type')
    order_date = fields.Datetime('Order Date')
    order_date_str = fields.Char('Order Date (str)') #GrabFoood ISO_8601/RFC3339.
    line_ids = fields.One2many('pos.online.outlet.order.line','order_id', string='Lines')
    order_data = fields.Text('Order Data')
    amount_total = fields.Float(string='Amount Total', compute='_compute_amount_total', store=True)
    amount_total_order = fields.Float('Amount Total Order')
    manual_action = fields.Char('Manual Action', help="Store value when Accept/Reject order from POS")
    currency_id = fields.Many2one('res.currency', string='Currency', related='online_outlet_id.currency_id')
    has_pos_order = fields.Boolean('Has Pos Order')
    status = fields.Char('Online Status Tracking', help="Tracking status from GrabFood/GoFood")
    online_state = fields.Char('Online Status', compute='_compute_online_state', tracking=True, store=True)
    state = fields.Selection([
        ('new','New'),
        ('to pay','To Pay'),
        ('paid','Paid'),
        ('cancel','Cancel'),
    ], string='Status', default='new', tracking=True)
    pos_order_count = fields.Integer(compute='_compute_pos_order_count', string="POS Orders (count)")
    payment_type = fields.Selection([('cash','Cash'), ('cashless','Cashless')], 'Payment Type')
    info = fields.Char('Info')

    #Grabfood
    is_mark_order_ready = fields.Boolean('Is Mark Order Ready?')
    order_ready_est_allow_change = fields.Boolean('Order Ready Estimation Allow Change')
    order_ready_est_time = fields.Char('Order Ready Estimation Time') #GrabFoood ISO_8601/RFC3339.
    order_ready_est_max_time = fields.Char('Order Ready Estimation Max Time') #GrabFoood ISO_8601/RFC3339.
    order_ready_new_est_time = fields.Char('Order Ready New Estimation Time') #GrabFoood ISO_8601/RFC3339.
    order_ready_est_time_display = fields.Datetime(string='Ready Time', compute='_compute_order_ready_est_time_display')
    exponent = fields.Integer('Exponent')
    #End Grabfood

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum([l.subtotal for l in rec.line_ids])

    def _compute_order_ready_est_time_display(self):
        for rec in self:
            display_date = False
            ready_time = rec.order_ready_est_time
            if rec.order_ready_new_est_time:
                ready_time = rec.order_ready_new_est_time
            if ready_time:
                try:
                    display_date = parser.parse(ready_time).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
                    
            rec.order_ready_est_time_display = display_date

    def _compute_pos_order_count(self):
        for rec in self:
            pos_order_count = self.env['pos.order'].sudo().search_count([('oloutlet_order_id','=', rec.id)])
            rec.pos_order_count = pos_order_count

    @api.depends('status')
    def _compute_online_state(self):
        for rec in self:
            status = rec.status
            online_state = rec.status
            if status in ['ACCEPTED', 'Accepted']:
                online_state = 'Order Accepted'
            if status in ['DRIVER_ALLOCATED']:
                online_state = 'Driver Allocated'
            if status in ['DRIVER_ARRIVED']:
                online_state = 'Driver Arrived'
            if status in ['COLLECTED']:
                online_state = 'Order Collected'
            if status in ['DELIVERED']:
                online_state = 'On Delivery'
            if status in ['FAILED']:
                online_state = 'Failed'
            if status in ['CANCELLED', 'Cancel', 'Rejected']:
                online_state = 'Cancelled'

            rec.online_state = online_state

    def action_view_pos_order(self):
        return {
            'name': _('Orders'),
            'res_model': 'pos.order',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('point_of_sale.view_pos_order_tree_no_session_id').id, 'tree'),
                (self.env.ref('point_of_sale.view_pos_pos_form').id, 'form'),
            ],
            'type': 'ir.actions.act_window',
            'domain': [('oloutlet_order_id', '=', self.id)],
        }

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self._context
        if 'ctx_limit' in context:
            limit = context['ctx_limit']
        if 'ctx_order_by' in context:
            order = context['ctx_order_by']
        return super(PosOnlineOutletOrder, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)


class PosOnlineOutletOrderLine(models.Model):
    _name = "pos.online.outlet.order.line"
    _description = "Pos Online Outlet Order Line"
    _order = "sequence asc"

    order_id = fields.Many2one('pos.online.outlet.order', 'Order')
    product_id = fields.Many2one('product.product', 'Product')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related="product_id.product_tmpl_id")
    description = fields.Char(string="Description", compute='_compute_description', store=True)    
    qty = fields.Integer('Quantity')
    price = fields.Float('Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    note = fields.Char('Note')
    is_delivery = fields.Boolean('Delivery')
    is_main_product = fields.Boolean('Is Main Product')
    is_option_product = fields.Boolean('Is Option Product')
    sequence = fields.Integer('Sequence')

    def _compute_description(self):
        for line in self:
            if line.product_id:
                line.description = line.product_id.name

    @api.depends('qty','price')
    def _compute_subtotal(self):
        for line in self:
            subtotal = line.qty * line.price
            line.subtotal = subtotal


class PosOnlineOutletSellingTime(models.Model):
    _name = "pos.online.outlet.selling.time"
    _description = "Pos Online Outlet Selling Time"
    
    name = fields.Char('Name')
    start_time = fields.Datetime('Start Time')
    end_time = fields.Datetime('End Time')

    monday = fields.Boolean('Monday')
    monday_start_time = fields.Float('Start Time', default=7.0)
    monday_end_time = fields.Float('End Time', default=22.0)

    tuesday = fields.Boolean('Tuesday')
    tuesday_start_time = fields.Float('Start Time', default=7.0)
    tuesday_end_time = fields.Float('End Time', default=22.0)

    wednesday = fields.Boolean('Wednesday')
    wednesday_start_time = fields.Float('Start Time', default=7.0)
    wednesday_end_time = fields.Float('End Time', default=22.0)

    thursday = fields.Boolean('Thursday')
    thursday_start_time = fields.Float('Start Time', default=7.0)
    thursday_end_time = fields.Float('End Time', default=22.0)

    friday = fields.Boolean('Friday')
    friday_start_time = fields.Float('Start Time', default=7.0)
    friday_end_time = fields.Float('End Time', default=22.0)

    saturday = fields.Boolean('Saturday')
    saturday_start_time = fields.Float('Start Time', default=7.0)
    saturday_end_time = fields.Float('End Time', default=22.0)
    
    sunday = fields.Boolean('Sunday')
    sunday_start_time = fields.Float('Start Time', default=7.0)
    sunday_end_time = fields.Float('End Time', default=22.0)

    def get_selling_times(self):
        OnlineOutlet = self.env['pos.online.outlet']
        selling_times = []
        for time in self.env[self._name].search([]):
            service_hours = {
                "mon": { "openPeriodType": "CloseAllDay", "periods": [] },
                "tue": { "openPeriodType": "CloseAllDay", "periods": [] },
                "wed": { "openPeriodType": "CloseAllDay", "periods": [] },
                "thu": { "openPeriodType": "CloseAllDay", "periods": [] },
                "fri": { "openPeriodType": "CloseAllDay", "periods": [] },
                "sat": { "openPeriodType": "CloseAllDay", "periods": [] },
                "sun": { "openPeriodType": "CloseAllDay", "periods": [] },
            }
            if time.monday:
                service_hours['mon'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.monday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.monday_end_time)
                    }]
                }

            if time.tuesday:
                service_hours['tue'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.tuesday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.tuesday_end_time)
                    }]
                }

            if time.wednesday:
                service_hours['wed'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.wednesday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.wednesday_end_time)
                    }]
                }

            if time.thursday:
                service_hours['thu'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.thursday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.thursday_end_time)
                    }]
                }
            if time.friday:
                service_hours['fri'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.friday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.friday_end_time)
                    }]
                }

            if time.saturday:
                service_hours['sat'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.saturday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.saturday_end_time)
                    }]
                }

            if time.sunday:
                service_hours['sun'] = {
                    "openPeriodType": "OpenPeriod",
                    "periods": [{
                        "startTime": OnlineOutlet.format24hour(time.sunday_start_time),
                        "endTime": OnlineOutlet.format24hour(time.sunday_end_time)
                    }]
                }
            selling_times += [{
                "startTime": time.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                "endTime": time.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                "id": "sellingTimeID-%s" % str(time.id),
                "name": time.name,
                "serviceHours": service_hours
            }]

        return selling_times