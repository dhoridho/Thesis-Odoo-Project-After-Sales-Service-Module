# -*- coding: utf-8 -*-

from odoo import fields, models, api
import qrcode
from io import BytesIO
import base64
from urllib.parse import urlparse


class AssetMoves(models.Model):
    _name = 'asset.moves'
    _description = "Asset Moves"
    _rec_name = 'asset_id'

    asset_id = fields.Many2one('maintenance.equipment', string="Name")
    owner_id = fields.Many2one('res.partner', string="Owner")
    held_by_id = fields.Many2one('res.partner', string="Held By")
    asset_moves_ids = fields.One2many('asset.moves.line', 'asset_move_id', string="Asset move lines")


class AssetMovesLine(models.Model):
    _name = 'asset.moves.line'

    asset_move_id = fields.Many2one('asset.moves', string="Asset id ref")
    asset_id = fields.Many2one('maintenance.equipment', string="Name")
    owner_id = fields.Many2one('res.partner', string="Owner")
    held_by_id = fields.Many2one('res.partner', string="Held By")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    @api.model
    def create(self, vals):
        result = super().create(vals)
        data_vals = {'start_date': result.create_date, 'held_by_id': result.held_by_id.id}
        self.env['asset.moves'].create({'asset_id': result.id, 'held_by_id': result.held_by_id.id, 'owner_id': result.owner.id, 'asset_moves_ids': [(0, 0, data_vals)]})
        barcode = self.env['ir.sequence'].next_by_code('maintenance.equipment.barcode.sequence')
        result.barcode = barcode

        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        parsed_url = urlparse(base_url)
        base_url = f'{parsed_url.netloc}/page/asset_information/?asset={result.id}'

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(base_url)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        result.qr_code = qr_image
        result.create_account_asset()
        return result


class EmployeeAssetTransfer(models.Model):
    _inherit = 'employee.asset.transfer'

    def action_done(self):
        res = super(EmployeeAssetTransfer, self).action_done()
        for rec in self.assets_line:
            asset_move_id = self.env['asset.moves'].search([('asset_id', '=', rec.asset_id.id)],limit=1)
            for record in asset_move_id.asset_moves_ids:
                if not record.end_date:
                    record.end_date = self.create_date
                else:
                    continue
            self.env['asset.moves.line'].create({'start_date': self.create_date, 'held_by_id': rec.employee_id.partner_id.id,
                                                 'asset_move_id': asset_move_id.id})
        return res
