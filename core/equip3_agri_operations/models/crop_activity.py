from odoo import models, fields


class CropActivity(models.Model):
    _inherit = 'crop.activity'

    account_id = fields.Many2one('account.account', string='Activity Account', required=True)
    asset_ids = fields.One2many('crop.activity.asset', 'activity_id', string='Assets')


class AgricultureCropActivityAsset(models.Model):
    _name = 'crop.activity.asset'
    _description = 'Crop Activity Asset'
    _rec_name = 'asset_id'

    activity_id = fields.Many2one('crop.activity', string='Activity', required=True, ondelete='cascade')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    user_id = fields.Many2one('res.users', required=True, string='Responsible')
