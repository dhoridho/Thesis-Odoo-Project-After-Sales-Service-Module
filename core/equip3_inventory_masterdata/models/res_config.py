from odoo import api, fields, models, _

class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        res = super(ResConfigSettingsInherit, self).set_values()
        if self.is_material_request_approval_matrix and self.inventory:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_material_menu').active = True
        else:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_material_menu').active = False
        if self.is_internal_transfer_approval_matrix and self.inventory:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_internal_transfer_menu').active = True
        else:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_internal_transfer_menu').active = False
        
        if self.is_stock_count_approval and self.inventory:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_stock_count_menu').active = True
        else:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_stock_count_menu').active = False
        if self.is_product_usage_approval and self.inventory:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_product_usage_menu').active = True
        else:
            self.env.ref('equip3_inventory_masterdata.approval_matrix_product_usage_menu').active = False
        return res
