from odoo import _, api, fields, models



class AssetQrcodeConfig(models.Model):
    _name = 'asset.qrcode.config'
    _description = 'Asset Qrcode Config'

    # @api.model
    # def _get_qrcode_field(self):
    #     field_list = []
    #     ir_model_id = self.env['ir.model'].search([('model', '=', 'maintenance.equipment')])
    #     if ir_model_id:
    #         for field in self.env['ir.model.fields'].search([
    #                  ('name', '!=', 'barcode'),
    #                  ('field_description', '!=', 'unknown'),
    #                  ('readonly', '=', False),
    #                  ('model_id', '=', ir_model_id.id),
    #                  ('ttype', '=', 'char')]):
    #             field_list.append((field.name, field.field_description))
    #     return field_list


    page_width = fields.Integer(string='Page Width', required=True, default=150, help="Page Width")
    page_height = fields.Integer(string='Page Height', required=True, default=170, help="Page Height")
    
    # Display field configuration
    asset_name = fields.Boolean('Asset Name', default=True)
    asset_value = fields.Boolean('Asset Value', default=True)
    serial_no = fields.Boolean('Serial Number', default=True)
    
    # Font size
    asset_name_size = fields.Char('Asset Name Font Size', default=7)
    asset_value_size = fields.Char('Asset Value Font Size', default=7)
    serial_no_size = fields.Char('Serial Number Font Size', default=7)
    
    # Qr code configuration
    margin_top = fields.Integer(string="Margin(Top)", required=True)
    margin_bottom = fields.Integer(string="Margin(Bottom)", required=True)
    margin_left = fields.Integer(string="Margin(Left)", required=True)
    margin_right = fields.Integer(string="Margin(Right)", required=True)
    dpi = fields.Integer(string="DPI", required=True)
    header_spacing = fields.Integer(string="Header Spacing", required=True)
    qrcode_width = fields.Integer(string="QR Code Width", required=True, default=51)
    qrcode_height = fields.Integer(string="QR Code Height", required=True, default=25)
    # qrcode_field = fields.Selection('_get_qrcode_field', string="QR Code Field")
    
    def apply(self):
        format_record = self.env.ref('equip3_asset_fms_masterdata.paperformat_config')
        if format_record:
            update_vals = {
                'page_height': self.page_height,
                'page_width': self.page_width,
                'margin_top': self.margin_top,
                'margin_bottom': self.margin_bottom,
                'margin_left': self.margin_left,
                'margin_right': self.margin_right,
                'dpi': self.dpi,
            }
            format_record.write(update_vals)
        return True

    
    @api.onchange('dpi')
    def onchange_dpi(self):
        if self.dpi < 80:
            self.dpi = 80