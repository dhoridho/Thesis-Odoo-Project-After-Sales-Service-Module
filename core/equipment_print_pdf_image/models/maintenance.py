# -*- coding: utf-8 -*-


from odoo import api, fields, models

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    equipmt_image1_custom = fields.Image(
        string='Image1'
    )
    equipmt_image2_custom = fields.Image(
        string='Image2'
    )
    equipmt_image3_custom = fields.Image(
        string='Image3'
    )
    equipmt_image4_custom = fields.Image(
        string='Image4'
    )
    equipmt_image5_custom = fields.Image(
        string='Image5'
    )
    equipmt_image6_custom = fields.Image(
        string='Image6'
    )
  