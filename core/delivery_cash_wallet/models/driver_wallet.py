from odoo import api, models, fields, _


class DriverWallet(models.Model):
    _name = "driver.wallet"
    _description = 'Driver Wallet'
    _rec_name = "delivery_boy_id"

    def _compute_mobile_location_cash(self):
        for rec in self:
            rec.mobile = rec.delivery_boy_id.mobile
            user_id = self.env['res.users'].search([('partner_id', '=', rec.delivery_boy_id.id)])
            store_config = self.env['store.configuration'].search([('delivery_boy_ids', '=', user_id.id)])
            rec.location_ids = [(6, 0, store_config.location_id.ids)]
            rec.cash_balance = 0.0

    location_ids = fields.Many2many("stock.location", string="Location",compute='_compute_mobile_location_cash')
    delivery_boy_id = fields.Many2one('res.partner',string= 'Name',
                                   domain="[('is_driver', '=', True), ('status','=','available')]")
    mobile = fields.Char(string="Mobile", compute='_compute_mobile_location_cash')
    cash_balance = fields.Float(string="Cash Balance",compute="_compute_mobile_location_cash")
    order_id = fields.Many2one("sale.order",string="Order")
