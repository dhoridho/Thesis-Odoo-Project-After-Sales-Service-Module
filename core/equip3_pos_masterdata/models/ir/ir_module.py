from odoo import models


class Module(models.Model):
    _inherit = "ir.module.module"

    def button_immediate_upgrade(self):
        res = super(Module, self).button_immediate_upgrade()

        if self.name in ["equip3_pos_masterdata"]:
            if self.env.ref('point_of_sale.barcode_rule_discount', raise_if_not_found=False):
                self.env.ref('point_of_sale.barcode_rule_discount').unlink()
            if self.env.ref('point_of_sale.barcode_rule_price_two_dec', raise_if_not_found=False):
                self.env.ref('point_of_sale.barcode_rule_price_two_dec').unlink()
            if self.env.ref('point_of_sale.barcode_rule_price_two_dec', raise_if_not_found=False):
                self.env.ref('point_of_sale.barcode_rule_price_two_dec').unlink()
            self.env['pos.config'].sudo().search([]).write({
                'group_pos_user_id':self.env.ref('equip3_pos_masterdata.group_pos_user').id,
                'group_pos_manager_id':self.env.ref('equip3_pos_masterdata.group_pos_manager').id,
            })
            self.env.ref('point_of_sale.access_pos_config_manager').active = False
            self.env.ref('point_of_sale.access_pos_config_user').active = False
            self.env.ref('point_of_sale.access_pos_order_line').active = False
            self.env.ref('point_of_sale.access_pos_order').active = False
            self.env.ref('point_of_sale.access_pos_order_stock_worker').active = False
            self.env.ref('point_of_sale.access_pos_session_user').active = False
            self.env.ref('equip3_pos_masterdata.menu_sale_coupon').active = False
            self.env.ref('point_of_sale.access_pos_payment_method_manager').active = False
            self.env.ref('point_of_sale.access_pos_payment_method_user').active = False
            self.env.ref('point_of_sale.pos_menu_products_attribute_action').active = False
            self.env.ref('point_of_sale.access_product_category_pos_manager').active = False
            self.env.ref('point_of_sale.access_product_category_pos_user').active = False
            
            if self.env.ref('point_of_sale.group_pos_manager'):
                self.env.ref('point_of_sale.group_pos_manager').write({'menu_access':False})
            if self.env.ref('point_of_sale.group_pos_user'):
                self.env.ref('point_of_sale.group_pos_user').write({'menu_access':False})

        return res