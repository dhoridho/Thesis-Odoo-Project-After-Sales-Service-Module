from odoo import api, fields, models


class MPTiktokWarehouse(models.Model):
    _name = 'mp.tiktok.warehouse'
    _inherit = 'mp.base'
    _description = 'Marketplace Tiktok Warehouse'
    _rec_name = 'warehouse_name'

    WAREHOUSE_TYPE = [
        ('1', 'SALES WAREHOUSE'),
        ('2', 'RETURN WAREHOUSE'),
        ('3', 'LOCAL RETURN WAREHOUSE'),
    ]
    WAREHOUSE_SUB_TYPE = [
        ('1', 'DOMESTIC WAREHOUSE'),
        ('2', 'CB OVERSEA WAREHOUSE'),
        ('3', 'CB DIRECT SHIPPING WAREHOUSE'),
    ]
    WAREHOUSE_EFFECT_STATUS = [
        ('1', 'EFFECTIVE'),
        ('2', 'NONEFFECTIVE'),
        ('3', 'RESTRICTED'),
    ]

    warehouse_id = fields.Char(string="Warehouse ID", readonly=True)
    warehouse_name = fields.Char(string="Warehouse Name", readonly=True)
    warehouse_type = fields.Selection(string="Warehouse Type", selection=WAREHOUSE_TYPE, readonly=True)
    warehouse_sub_type = fields.Selection(string="Warehouse Sub Type", selection=WAREHOUSE_SUB_TYPE, readonly=True)
    warehouse_effect_status = fields.Selection(string="Warehouse Effect Type",
                                               selection=WAREHOUSE_EFFECT_STATUS, readonly=True)
    region = fields.Char(string="Region", readonly=True)
    state = fields.Char(string="State", readonly=True)
    city = fields.Char(string="City", readonly=True)
    district = fields.Char(string="District", readonly=True)
    town = fields.Char(string="Town", readonly=True)
    zipcode = fields.Char(string="Zipcode", readonly=True)
    phone = fields.Char(string="Phone", readonly=True)
    contact_person = fields.Char(string="Contact Person", readonly=True)
