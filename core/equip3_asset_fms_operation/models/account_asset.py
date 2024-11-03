from odoo import models, fields, api, _


class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'

    show_sale_dispose = fields.Boolean("Show Sale Button",compute='check_equipment_created')
    show_dispose = fields.Boolean("Show Dispose",compute='check_equipment_created')

    def check_equipment_created(self):
        for rec in self:
            equip_ids = self.env['maintenance.equipment'].search([('account_asset_id','=',rec.id)]).ids
            if not equip_ids:
                if rec.state == 'open':
                    rec.show_sale_dispose  = True
                    rec.show_dispose = True
                else:
                    rec.show_sale_dispose = False
                    rec.show_dispose = False
            else:
                if rec.state == 'open':
                    rec.show_sale_dispose = True
                    rec.show_dispose = False
                else:
                    rec.show_sale_dispose = False
                    rec.show_dispose = False

AccountAssetAsset()
