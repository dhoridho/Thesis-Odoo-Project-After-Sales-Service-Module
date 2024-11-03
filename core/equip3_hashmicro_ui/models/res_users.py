from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = "res.users"

    equip_theme_color = fields.Selection([
        ('black', 'Black'),
        ('red', 'Red'),
        ('blue', 'Blue'),
        ('gray', 'Gray'),
        ('topaz_blue', 'Topaz Blue'),
        ('white', 'White'),
    ], default='black')

    @api.model
    def change_equip_theme(self, user_id, theme):
        user_id = self.env['res.users'].browse(user_id).sudo()
        return user_id.write({'equip_theme_color': theme})

    # to delete once module upgraded
    @api.model
    def delete_custom_scss(self):
        attachment_ids = self.env['ir.attachment'].sudo().search([
            ('name', 'ilike', 'colors.custom.equip3_hashmicro_ui'), 
            ('mimetype', '=', 'text/scss')
        ])
        if attachment_ids:
            attachment_ids.unlink()
        
        asset_id = self.env.ref('equip3_hashmicro_ui._assets_primary_variables', raise_if_not_found=False)
        if asset_id:
            inherited_view_ids = self.env['ir.ui.view'].sudo().search([('inherit_id', '=', asset_id.id)])
            if inherited_view_ids:
                inherited_view_ids.unlink()
