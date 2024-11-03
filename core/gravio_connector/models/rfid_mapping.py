from odoo import models, api, fields
import json


class RfidMapping(models.Model):
    _name = 'rfid.mapping'
    _description = 'RFID Mapping'
    
    process_type = fields.Selection(string='Process', selection=[('rn', 'Create Receiving Note'), ('do', 'Create Delivery Order'), ('it','Create Interwarehouse Transfer')], required=True)
    location_id = fields.Many2one('stock.location', string='When Product Detected In', required=True)
    layer = fields.Char(string='Layer')

    
    @api.onchange('location_id','process_type')
    def onchange_location_id(self):
        if self.location_id:
            self.layer = self.location_id.layer_label
