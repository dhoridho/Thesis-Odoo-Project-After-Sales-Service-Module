from odoo import api, models, fields, tools

class RejectPickingOrder(models.Model):
    _name = "reject.picking.order"
    _description = 'Reject Picking Order'
    
    driver_id = fields.Many2one('res.partner','Delivery Boy',domain="[('is_driver', '=', True),('status','=','available')]")
    picking_id = fields.Many2one('picking.order',string="Picking Order")
    assign_date = fields.Datetime(string="Assign Date")
    reject_date = fields.Datetime(string="Reject Date")
    reject_reason = fields.Text(string="Reject Reason")
