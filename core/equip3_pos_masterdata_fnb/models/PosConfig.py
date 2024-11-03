# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    floor_ids = fields.Many2many(
        'restaurant.floor',
        'pos_config_restaurant_floor_rel',
        'pos_config_id',
        'floor_id',
        string="Floors",
        domain=[('id', '!=', None)]
    )
    
    checker_screen = fields.Boolean('Kitchen Checker Screen', default=False)
    kitchen_screen = fields.Boolean(
        'Kitchen Order Tickets (KOT)',
        help='Example Waiter Delivery Man need management Tickets for delivery Products to Customers \n'
             'Checked to this field for them can see Tickets Kitchen Screen', default=False
    )
    takeaway_screen = fields.Boolean(
        'Takeaway Screen',
        help='Example Waiter Delivery Man need management Tickets for Take Away Products to Customers \n'
            'Checked to this field for them can see Tickets Take Away Screen', default=False
    )
    takeaway_order = fields.Boolean(
        'Take Away Order',
        default=0,
        help='It is type of Submit Kitchen Order Ticket \n'
             'Normally when add products to Card and click Order Button, it default Order for Customer come restaurant and sit down at Table \n'
             'Take Away is customer come Restaurant and Order and Leave when Order Done. \n'
             'Take Away only difference Order basic of Odoo is packaging \n'
             'And allow Kitchen Know Order is basic or Take Away for packaging'
    )

    auto_order = fields.Boolean(
        'Auto Submit Order to KOT Screen',
        help='When it checked, when waiters take Order for customer finished \n'
             'And go back Floor Screen, POS auto Order to Kitchen Screen',
        default=False
    )
    sync_manual_button = fields.Boolean(
        'Sync Manual Order',
        help='Allow POS Session of This Config send Orders to another Sessions direct \n'
             'If another Sessions have the same Order with current Sessions \n'
             'Orders of another Sessions will replace by Orders send from current Session',
        default=False)
    send_order_to_kitchen = fields.Boolean(
        'Send Order to Kitchen',
        default=0,
        help='Check if need waiters/cashiers send order information to kitchen/bar room without printers')

    allow_lock_table = fields.Boolean(
        'Lock Table',
        default=0,
        help='If Customer Booked Table, you can lock talbe \n'
             'Unlock by Pos Pass In of Managers Validation')
    
    allow_split_table = fields.Boolean('Allow Split Table')
    allow_merge_table = fields.Boolean('Merge/Combine Tables')
    required_set_guest = fields.Boolean(
        'Auto ask Guests when add new Order')
    set_guest = fields.Boolean('Set Guests', default=0)
    set_guest_when_add_new_order = fields.Boolean(
        'Auto Ask Guests',
        help='When Cashiers add Orders, pos auto popup and ask guest name and guest number')

    allow_merge_lines = fields.Boolean(
        'Allow Merge Lines',
        help='If checked, allow automatic merge new line the same Product to line has submited to Kitchen Receipt'
    )

    table_reservation_list = fields.Boolean(string="Table Reservation List", default=False)
    allow_kitchen_cancel = fields.Boolean(
        'Allow Kitchen Cancel',
        help='Allow Kitchen Users Cancel request from waiter because some reasons'
    )
    period_minutes_warning = fields.Float(
        'Period Minutes Warning Kitchen',
        default=15,
        help='Example input 15 (minutes) here, of each line request from Waiter to Kitchen \n'
             'have waiting (processing) times bigger than 15 minutes \n'
             'Item requested by Waiters on Kitchen Screen auto highlight red color'
    )
    required_input_reason_cancel = fields.Boolean(
        'Required Reason Cancel',
        help='When Kitchen Users cancel Line required input reason'
    )
    reason_cancel_reason_ids = fields.Many2many(
        'pos.tag',
        'cancel_reason_tag_rel',
        'config_id',
        'tag_id',
        string='Cancel Reason'
    )

    is_complementary = fields.Boolean(string="Complementary")
    complementary_journal_id = fields.Many2one(
        'account.journal',
        string='Default Complementary Journal',
    )
    required_ask_seat = fields.Boolean(string="Auto Ask Seat Number when add new product", default=False)

    employee_meal = fields.Boolean('Employee Meal')
    employee_meal_limit_budget = fields.Float('Employee Meal Limit Budget')

    @api.onchange('screen_type')
    def _onchange_screen_type_mod(self):
        self.sync_multi_session = self.screen_type in ('kitchen', 'takeaway')

    @api.onchange('hide_order_screen')
    def onchange_hide_screen(self):
        if self.hide_order_screen:
            self.takeaway_screen = False
            self.kitchen_screen = True
        else:
            self.takeaway_screen = False
            self.kitchen_screen = False

    @api.onchange('screen_type')
    def _onchange_kitchen_screen_setting_mod(self):
        if self.screen_type == 'kitchen':
            self.hide_order_screen = True
            self.checker_screen = True
            self.kitchen_screen = True
            self.takeaway_screen = False
            self.takeaway_order = False
            self.auto_order = True
            self.sync_manual_button = True
            self.send_order_to_kitchen = True
            self.allow_lock_table = False
            self.table_reservation_list = False
        elif self.screen_type == 'takeaway':
            self.hide_order_screen = True
            self.checker_screen = False
            self.kitchen_screen = False
            self.takeaway_screen = True
            self.takeaway_order = True
            self.auto_order = False
            self.sync_manual_button = False
            self.send_order_to_kitchen = True
            self.allow_lock_table = False
            self.table_reservation_list = False

    @api.onchange('allow_split_table')
    def _onchange_allow_split_table(self):
        if self.allow_split_table:
            self.iface_splitbill = True