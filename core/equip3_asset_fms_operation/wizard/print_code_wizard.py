# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import ValidationError

class PrintAssetQRCodeWizard(models.TransientModel):
    _name = 'print.asset.qrcode.wizard'
    _description = 'Print Asset QR Code (PDF)'

    paperformat_id = fields.Many2one('report.paperformat', string='Paper Format')
    allowed_paperformat_ids = fields.Many2many('report.paperformat', string='Allowed Paper Format', compute='_compute_allowed_paperformat_ids')
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(PrintAssetQRCodeWizard, self).default_get(fields_list)
        defaults['paperformat_id'] = self.env.ref('equip3_asset_fms_masterdata.paperformat_config').id
        return defaults

    @api.depends('paperformat_id')
    def _compute_allowed_paperformat_ids(self):
        allowed_paperformat_ids = [
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a0_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a1_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a2_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a3_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a4_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a5_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a6_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a7_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a8_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a9_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a10_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_config').id,
        ]
        for rec in self:
            rec.allowed_paperformat_ids = self.env['report.paperformat'].browse(allowed_paperformat_ids)

    def action_confirm(self):
        context = dict(self._context or {})
        report_action = self.env['ir.actions.report'].search([('report_name', '=', 'equip3_asset_fms_masterdata.report_maintenance_equipment_qrcode_new')], limit=1)
        paperformat_config = self.env.ref('equip3_asset_fms_masterdata.paperformat_config')
        report_action.write({'paperformat_id': paperformat_config.id})
        return report_action.report_action(self.env['maintenance.equipment'].browse(context.get('active_ids')))
    
    
class PrintAssetBarcodeWizard(models.TransientModel):
    _name = 'print.asset.barcode.wizard'
    _description = 'Print Asset Barcode (PDF)'

    paperformat_id = fields.Many2one('report.paperformat', string='Paper Format')
    allowed_paperformat_ids = fields.Many2many('report.paperformat', string='Allowed Paper Format', compute='_compute_allowed_paperformat_ids')

    @api.depends('paperformat_id')
    def _compute_allowed_paperformat_ids(self):
        allowed_paperformat_ids = [
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a0_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a1_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a2_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a3_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a4_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a5_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a6_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a7_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a8_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a9_asset').id,
            self.env.ref('equip3_asset_fms_masterdata.paperformat_a10_asset').id,
        ]
        for rec in self:
            rec.allowed_paperformat_ids = self.env['report.paperformat'].browse(allowed_paperformat_ids)

    def action_confirm(self):
        context = dict(self._context or {})
        report_action = self.env['ir.actions.report'].search([('report_name', '=', 'equip3_asset_fms_masterdata.report_maintenance_equipment_asset_barcode')], limit=1)
        report_action.write({'paperformat_id': self.paperformat_id.id})
        return report_action.report_action(self.env['maintenance.equipment'].browse(context.get('active_ids')))