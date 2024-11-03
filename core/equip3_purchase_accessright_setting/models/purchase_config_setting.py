from datetime import datetime
from odoo import models,fields,api,_


class PurchaseConfigSetting(models.Model):
    _name = 'purchase.config.settings'

    name = fields.Char("Name")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    purchase_revision = fields.Boolean("Enable Purchase Revisions", company_dependent=True)
    reference_formatting = fields.Selection([
        ("revise","Revise Reference"),
        ("new","New Reference")
    ], string='Reference Formatting', company_dependent=True, default="revise", help=_("This default value is applied to any Revise Purchase Order created. Example: PO/G/YY/MM/DD/001/R01"))

    def save_config(self):
        # Simpan konfigurasi
        self.write({
            'purchase_revision': self.purchase_revision,
            'reference_formatting': self.reference_formatting,
        })

        # Kembali ke form view dalam mode edit setelah menyimpan
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.config.settings',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_purchase_accessright_setting.purchase_config_setting_view_form').id,
            'res_id': self.id,  # ID dari record yang disimpan
            'target': 'inline',  # Menjaga tampilan tetap di tab yang sama
        }