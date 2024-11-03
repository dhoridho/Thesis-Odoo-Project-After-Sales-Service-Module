
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_it_barcode_mobile_type = fields.Selection(string='Product Scan Options In Mobile (Internal Transfer)',
                                                    related="company_id.sh_it_barcode_mobile_type", translate=True, readonly=False)

    sh_it_bm_is_cont_scan = fields.Boolean(
        string='Continuously Scan? (Internal Transfer)', related="company_id.sh_it_bm_is_cont_scan", readonly=False)

    sh_it_bm_is_notify_on_success = fields.Boolean(
        string='Notification On Product Succeed? (Internal Transfer)', related="company_id.sh_it_bm_is_notify_on_success", readonly=False)

    sh_it_bm_is_notify_on_fail = fields.Boolean(
        string='Notification On Product Failed? (Internal Transfer)', related="company_id.sh_it_bm_is_notify_on_fail", readonly=False)

    sh_it_bm_is_sound_on_success = fields.Boolean(
        string='Play Sound On Product Succeed? (Internal Transfer)', related="company_id.sh_it_bm_is_sound_on_success", readonly=False)

    sh_it_bm_is_sound_on_fail = fields.Boolean(
        string='Play Sound On Product Failed? (Internal Transfer)', related="company_id.sh_it_bm_is_sound_on_fail", readonly=False)

    sh_it_bm_is_add_product = fields.Boolean(
        string="Is add new product in picking? (Internal Transfer)", related="company_id.sh_it_bm_is_add_product", readonly=False)
    
    sh_it_mobile_barcode_type = fields.Selection(string='Barcode Scan Options', selection=[(
        'sku', 'SKU'), ('lot_serial', 'Lot / Serial Number')], config_parameter='equip3_inventory_scanning.sh_it_mobile_barcode_type', default='sku')
    