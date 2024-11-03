from odoo import api, models, fields

class stock_warehouse(models.Model):
    _inherit = "stock.warehouse"

    driver_ids = fields.One2many('stock.warehouse.driver','warehouse_id',string="Delivery Boy")


class stock_warehouse_driver(models.Model):
    _name = "stock.warehouse.driver"
    _description = 'Stock Warehouse Driver'
    
    driver_id = fields.Many2one('res.partner',string="Delivery Boy")
    warehouse_id = fields.Many2one('stock.warehouse',string="Warehouse")
    status = fields.Selection([('available','Available'),('not_available','Not Available')],'Status',default='available') 
