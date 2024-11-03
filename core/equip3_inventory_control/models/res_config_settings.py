# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    product_expiry = fields.Integer(string="Product Usage Expiry", help="The Expiry Date field on the Internal Transfer Request form will automatically be filled with the date and time based on the day period you fill in here.")
    expiry_days_select = fields.Selection([('before', 'Before'), ('after', 'After')])
    group_analytic_tags = fields.Boolean(string='Analytic Tags', implied_group='analytic.group_analytic_tags')
    pu_barcode_mobile_type = fields.Selection([
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('sh_qr_code', 'QR code'),
        ('all', 'All')
    ], default='barcode', string='Product Scan Options In Mobile (Product Usage)',)
    pu_bm_is_cont_scan = fields.Boolean(
        string='Continuously Scan? (Product Usage)')
    pu_bm_is_notify_on_success = fields.Boolean(
        string='Notification On Product Succeed? (Product Usage)')
    pu_bm_is_notify_on_fail = fields.Boolean(
        string='Notification On Product Failed? (Product Usage)')
    pu_bm_is_sound_on_success = fields.Boolean(
        string='Play Sound On Product Succeed? (Product Usage)')
    pu_bm_is_sound_on_fail = fields.Boolean(
        string='Play Sound On Product Failed? (Product Usage)')
    pu_bm_is_add_product = fields.Boolean(
        string="Is add new product in Product Usage? (Product Usage)")
    mandatory_freeze_inventory = fields.Boolean(string='Mandatory Freeze Inventory')

    stock_inventory_validation_scheduler = fields.Boolean(string='Stock Count Scheduler')
    stock_inventory_validation_per_batch = fields.Integer(string='Stock Count Lines per Batch')

    stock_scrap_validation_scheduler = fields.Boolean(string='Product Usage Scheduler', config_parameter='equip3_inventory_control.stock_scrap_validation_scheduler', default=False)
    stock_scrap_validation_per_batch = fields.Integer(string='Product Usage Lines per Batch', config_parameter='equip3_inventory_control.stock_scrap_validation_per_batch', default=500)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        product_usage_logs_menu = self.env.ref('equip3_inventory_control.menu_action_view_stock_scrap_request_log', raise_if_not_found=False)

        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'product_expiry': int(IrConfigParam.get_param('product_expiry', 0)),
            'expiry_days_select':IrConfigParam.get_param('expiry_days_select','before'),
            'group_analytic_tags': IrConfigParam.get_param('group_analytic_tags', False),
            'pu_barcode_mobile_type': IrConfigParam.get_param('pu_barcode_mobile_type', 'barcode'),
            'pu_bm_is_cont_scan': IrConfigParam.get_param('pu_bm_is_cont_scan', False),
            'pu_bm_is_notify_on_success': IrConfigParam.get_param('pu_bm_is_notify_on_success', False),
            'pu_bm_is_notify_on_fail': IrConfigParam.get_param('pu_bm_is_notify_on_fail', False),
            'pu_bm_is_sound_on_success': IrConfigParam.get_param('pu_bm_is_sound_on_success', False),
            'pu_bm_is_sound_on_fail': IrConfigParam.get_param('pu_bm_is_sound_on_fail', False),
            'pu_bm_is_add_product': IrConfigParam.get_param('pu_bm_is_add_product', False),
            'mandatory_freeze_inventory': IrConfigParam.get_param('mandatory_freeze_inventory', False),
            'stock_scrap_validation_scheduler': product_usage_logs_menu.active if product_usage_logs_menu else False
        })
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        IrConfigParam.set_param('product_expiry', self.product_expiry)
        IrConfigParam.set_param('expiry_days_select', self.expiry_days_select)
        IrConfigParam.set_param('group_analytic_tags', self.group_analytic_tags)

        IrConfigParam.set_param('pu_barcode_mobile_type', self.pu_barcode_mobile_type)
        IrConfigParam.set_param('pu_bm_is_cont_scan', self.pu_bm_is_cont_scan)
        IrConfigParam.set_param('pu_bm_is_notify_on_success', self.pu_bm_is_notify_on_success)
        IrConfigParam.set_param('pu_bm_is_notify_on_fail', self.pu_bm_is_notify_on_fail)
        IrConfigParam.set_param('pu_bm_is_sound_on_success', self.pu_bm_is_sound_on_success)
        IrConfigParam.set_param('pu_bm_is_sound_on_fail', self.pu_bm_is_sound_on_fail)
        IrConfigParam.set_param('pu_bm_is_add_product', self.pu_bm_is_add_product)
        IrConfigParam.set_param('mandatory_freeze_inventory', self.mandatory_freeze_inventory)

        if self.is_inventory_adjustment_with_value:
            self.env.ref('equip3_inventory_control.menu_accounting_inventory').active = True
        else:
            self.env.ref('equip3_inventory_control.menu_accounting_inventory').active = False

        product_usage_logs_menu = self.env.ref('equip3_inventory_control.menu_action_view_stock_scrap_request_log', raise_if_not_found=False)
        if product_usage_logs_menu:
            product_usage_logs_menu.active = self.stock_scrap_validation_scheduler
        return res
