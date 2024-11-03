
from odoo import models, fields, _


class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'
    
    def set_values(self):
        super(ResConfigSetting, self).set_values()
        if self.is_purchase_request_assign_user:
            # self.env.ref("equip3_purchase_rental.menu_purchase_request_line_rental_categ").active = True
            self.env.ref("equip3_purchase_rental.menu_purchase_request__line_rental").active = False
            self.env.ref("equip3_purchase_rental.menu_purchase_request_line_rental_assigned").active = True
            self.env.ref("equip3_purchase_rental.menu_purchase_request_line_rental_not_assigned").active = True
        else:
            # self.env.ref("equip3_purchase_rental.menu_purchase_request_line_rental_categ").active = False
            self.env.ref("equip3_purchase_rental.menu_purchase_request__line_rental").active = True
            self.env.ref("equip3_purchase_rental.menu_purchase_request_line_rental_assigned").active = False
            self.env.ref("equip3_purchase_rental.menu_purchase_request_line_rental_not_assigned").active = False