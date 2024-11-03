# -*- coding: utf-8 -*-
import hashlib
from odoo import api, models, fields, _
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_discount = fields.Boolean('Allow Change Discount', default=1)
    allow_qty = fields.Boolean('Allow Change Quantity', default=1)
    allow_price = fields.Boolean('Allow Change Price', default=1)
    allow_remove_line = fields.Boolean('Allow Remove Line', default=1)
    allow_minus = fields.Boolean('Allow Minus (+/-)', default=1)
    allow_payment = fields.Boolean('Allow Payment', default=1)
    allow_customer = fields.Boolean('Allow set Customer', default=1)
    allow_add_order = fields.Boolean('Allow Add Order', default=1)
    allow_remove_order = fields.Boolean('Allow Remove Order', default=1)
    allow_add_product = fields.Boolean('Allow Add Product', default=1)
    allow_payment_zero = fields.Boolean(
        'Allow Payment Zero',
        default=1,
        help='If active, cashier can made order total amount smaller than or equal 0')
    allow_offline_mode = fields.Boolean(
        'Allow Offline Mode',
        default=1,
        help='Required Internet of Cashiers Counter Devlice used POS Session online \n'
             'If have problem internet of Cashier Counter, POS not allow submit Orders to Backend \n'
             'Example Case Problem: \n'
             '1) Intenet Offline , Cashiers submit orders to Odoo server and not success \n'
             '2) And then them clear cache browse , and orders save on Cache of Browse removed \n'
             '- It mean all orders will lost \n'
             'So this function active, when any Orders submit to backend, POS auto check Odoo server online or not. If online allow Validate Order'
    )

    def get_user_pos_security_pin(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            return []
        # Apply visibility filters (record rules)
        visible_user_ids = self.search([('id', 'in', self.ids)])
        users_data = self.sudo().search_read([('id', 'in', visible_user_ids.ids)], ['pos_security_pin','cashier_code'])
        for user in users_data:
            user['pos_security_pin'] = hashlib.sha1(str(user['pos_security_pin']).encode('utf8')).hexdigest() if user['pos_security_pin'] else False
        return users_data

    def unlink(self):
        configs_with_users = self.env['pos.config'].search([('module_pos_hr', '=', 'True')]).filtered(lambda c: c.current_session_id)
        configs_with_all_users = configs_with_users.filtered(lambda c: not c.user_ids)
        configs_with_specific_users = configs_with_users.filtered(lambda c: c.user_ids & self)
        if configs_with_all_users or configs_with_specific_users:
            error_msg = _("You cannot delete an user that may be used in an active PoS session, close the session(s) first: \n")
            for user in self:
                config_ids = configs_with_all_users | configs_with_specific_users.filtered(lambda c: user in c.user_ids)
                if config_ids:
                    error_msg += _("User: %s - PoS Config(s): %s \n") % (user.name, ', '.join(config.name for config in config_ids))
            raise UserError(error_msg)
        return super(ResUsers, self).unlink()
