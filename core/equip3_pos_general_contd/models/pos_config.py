# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from odoo.exceptions import UserError
    
class PosConfig(models.Model):
    _inherit = "pos.config"

    screen_type = fields.Selection(selection_add=[
        ('kitchen', 'Kitchen Order Tickets (KOT) Screen'),
        ('takeaway', 'Takeaway Screen')
    ],
        string='Screen Type',
        default='cashier',
        help='Waiter Screen: is screen of waiters/cashiers take Order and submit Order to Kitchen\n'
             'Kitchen Screen: is screen of kitchen users save requested of Waiters/Cashiers'
    )

    is_allow_product_exchange = fields.Boolean('Allow Exchange')
    product_exchange_pin_ids = fields.Many2many('res.users',
        'pos_config_users_product_exchange_pin_rel', 'pos_config_id', 'user_id', string='Exchange PIN')
    product_exchange_line_pins = fields.Char(compute='_compute_product_exchange_line_pins', string='Exchange Line PINs')

    is_save_order_history_local = fields.Boolean('Save Order to Local Storage', default=True)
    save_order_history_local_days = fields.Integer('Save Order to Local Storage (Days)', default=5)

    is_save_order_to_pos_cache_service = fields.Boolean('Save Order to External POS Cache', default=True)
    link_pos_cache_service = fields.Char(string="Localhost link POS Cache (Service)", 
        help="Localhost link for store session order data to POS Cache (APK Service)\nProd: http://localhost:8080", 
        default='http://localhost:8080')

    @api.depends('product_exchange_pin_ids')
    def _compute_product_exchange_line_pins(self):
        for record in self:
            user_pin_data = []
            if record.is_allow_product_exchange:
                for user in record.product_exchange_pin_ids:
                    if user.pos_security_pin:
                        user_pin_data.append(str(user.pos_security_pin))
            record.product_exchange_line_pins = ','.join(pin for pin in user_pin_data)

    @api.onchange('is_save_order_history_local')
    def onchange_save_order_history_local_days(self):
        if self.save_order_history_local_days < 3:
            self.save_order_history_local_days = 3
        if self.save_order_history_local_days > 30:
            self.save_order_history_local_days = 30

    def write(self, vals):
        res = super(PosConfig, self).write(vals)
        self.check_order_history_local_days(vals)
        return res

    @api.model
    def create(self, vals):
        res = super(PosConfig, self).create(vals) 
        self.check_order_history_local_days(vals)
        return res

    def check_order_history_local_days(self, vals):
        if 'save_order_history_local_days' in vals:
            days = vals['save_order_history_local_days']
            if days > 30:
                raise UserError('Max Save Order to Local Storage (Days) is: 30 days')
            days = vals['save_order_history_local_days']
            if days < 1:
                raise UserError('Limit Save Order to Local Storage (Days) is: 1 days')
