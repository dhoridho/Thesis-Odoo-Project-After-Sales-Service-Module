# -*- coding: utf-8 -*-

import base64

from reportlab.graphics.barcode import createBarcodeDrawing

from odoo.http import request
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class RestaurantTable(models.Model):
    _inherit = "restaurant.table"

    locked = fields.Boolean('Manual Locked (Reservation)')
    is_check_locked = fields.Boolean('Locked (Reservation)',compute='_compute_is_check_locked', inverse='_set_check_locked')
    user_ids = fields.Many2many(
        'res.users',
        'restaurant_table_res_users_rel',
        'table_id',
        'user_id',
        string='Assign Users',
        help='Only Users assigned here only see tables assigned on POS Tables Screen'
    )
    barcode_url = fields.Char(
        string='QR Barcode URL',
        help='You can print this Barcode on header Print Button \n'
             'Customer come your restaurant and use them self Mobile scan this code \n'
             'Scan succeed, on mobile of Customer auot open new link for order product'
    )
    qr_image = fields.Binary('Barcode of Table')
    pricelist_id = fields.Many2one('product.pricelist', 'Special Pricelist')
    
    customer_name = fields.Char(string="Customer")
    date_reserve = fields.Datetime(string="Date Reserve")
    tbl_moved_from = fields.Many2one('restaurant.table',string="Moved from")
    clear_interval = fields.Char(string="Clear Interval")
    guest = fields.Char(string="Cashier Guest")
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)

    def _compute_is_check_locked(self):
        for data in self:
            is_check_locked = False
            if data.locked:
                is_check_locked = True
            if data.date_reserve and fields.Datetime.now() >= data.date_reserve:
                is_check_locked = True
            data.is_check_locked = is_check_locked

    def _set_check_locked(self):
        for data in self:
            data.locked = data.is_check_locked


    def render_image_base64(self, value, width, hight, hr, code='QR'):
        options = {}
        if hr: options['humanReadable'] = True
        try:
            res = createBarcodeDrawing(code, value=str(value), **options)
        except ValidationError as e:
            raise ValueError(e)
        return base64.encodestring(res.asString('jpg'))

    def initialization_qrcode(self):
        base_domain_system = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not base_domain_system or base_domain_system == 'http://localhost:8069':
            raise UserError(_(
                'Error !!! Your Server required hosting Online because customer scan QrCode, \n'
                'and go to your Server address online. \n'
                'If setup localhost or local your network, feature can not work'))
        config = self.env['pos.config'].sudo().search(
            [('restaurant_order', '=', True), ('restaurant_order_login', '!=', None),
             ('restaurant_order_password', '!=', None)], limit=1)
        if not config:
            raise UserError(_(
                'Error !!! Please set 1 POS Config is Restaurant Order. Please go to create new POS Config, go to tab Sync Between Session and active feature Restaurant Order'))
        try:
            uid = request.session.authenticate(request.session.db, config.restaurant_order_login,
                                               config.restaurant_order_password)
        except:
            raise UserError(_(
                'Error !!! Please checking:  \n'
                'Restaurant Order Login and Password of POS Config %s \n'
                'It is wrong login or password.', config.name))
        tables = self.sudo().search([])
        for table in tables:
            barcode_url = "%s/public/posodoo?table_id=%s&config_id=%s" % (
                base_domain_system, table.id, config.id)
            image = self.render_image_base64(barcode_url, code='QR', width=150, hight=150, hr=True)
            table.sudo().write({
                'qr_image': image,
                'barcode_url': barcode_url
            })
        return {
            'name': 'Successfully Setup',
            'res_model': 'ir.actions.act_url',
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': base_domain_system + '/web/login'
        }

    def lock_table(self, vals):
        return self.write(vals)

    def get_reserve_order(self, vals=None):  
        context = self._context
        domain = [
            ('table_no','=',vals['table_no']),
            ('table_floor','=',vals['table_floor'] ),
            ('state','in',['arrived','reserved']),
            ('reservation_from','<=',vals['reservation_to']),
            ('reservation_to','>=',vals['reservation_from']),
        ]
        reserve_order = self.env['reserve.order'].sudo().search_read(domain, limit=1)
        if reserve_order:
            return reserve_order[0]
        return {}


class RestaurantTable(models.Model):
    _inherit = "restaurant.floor"

    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist',
        help='Pricelist of Floor will apply to new Order of this Floor')

    def write(self, vals):
        res = super(RestaurantTable, self).write(vals)
        if vals.get('pricelist_id', None):
            for floor in self:
                floor.table_ids.write({'pricelist_id': floor.pricelist_id})
        return res
