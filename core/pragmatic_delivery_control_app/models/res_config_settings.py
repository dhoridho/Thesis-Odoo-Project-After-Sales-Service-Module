from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # group_delivery_boy_store_configuration = fields.Boolean("Enable Delivery Boy Location", implied_group='pragmatic_delivery_control_app.group_delivery_boy_store_configuration')
    automatic_confirm_saleorder = fields.Boolean("Automatic Confirmation E-Commerce Order")
    automatic_invoice_create = fields.Boolean("Automatic Generate Invoice",default=False)
    is_delivery_acknowledgement = fields.Boolean('Delivery Acknowledgement', default=False)
    is_broadcast_order = fields.Boolean(string="Broadcast Order", default=False)
    module_pragmatic_portal_user = fields.Boolean(string="Enable Delivery Boy Portal")
    module_pragmatic_delivery_acknowledgement = fields.Boolean(string="Enable Customer Acknowledgement")
    module_pragmatic_website_cash_on_delivery = fields.Boolean(string="Enable Cash On Delivery")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        Param = self.env['ir.config_parameter'].sudo()
        res['automatic_confirm_saleorder'] = Param.sudo().get_param('pragmatic_delivery_control_app.automatic_confirm_saleorder')
        res['automatic_invoice_create'] = Param.sudo().get_param('pragmatic_delivery_control_app.automatic_invoice_create')
        res['default_invoice_policy'] = Param.sudo().get_param('sale.default_invoice_policy')
        res['is_delivery_acknowledgement'] = Param.sudo().get_param('pragmatic_delivery_control_app.is_delivery_acknowledgement')
        res['is_broadcast_order'] = Param.sudo().get_param('pragmatic_delivery_control_app.is_broadcast_order')
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        draft_stages = self.env['order.stage'].search([('action_type', '=', 'draft')])
        if self.automatic_confirm_saleorder:
            for stage in draft_stages:
                stage.is_hidden = True
        else:
            for stage in draft_stages:
                stage.is_hidden = False
        if self.automatic_invoice_create:
            self.default_invoice_policy = 'order'
            self.env['ir.config_parameter'].sudo().set_param('sale.default_invoice_policy',self.default_invoice_policy)
        else:
            self.default_invoice_policy = 'delivery'
            self.env['ir.config_parameter'].sudo().set_param('sale.default_invoice_policy', self.default_invoice_policy)
        self.env['ir.config_parameter'].sudo().set_param(
            'pragmatic_delivery_control_app.automatic_confirm_saleorder',self.automatic_confirm_saleorder)
        self.env['ir.config_parameter'].sudo().set_param(
            'pragmatic_delivery_control_app.automatic_invoice_create', self.automatic_invoice_create)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_delivery_control_app.is_broadcast_order', self.is_broadcast_order)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_delivery_control_app.is_delivery_acknowledgement',self.is_delivery_acknowledgement)

        picking_type_obj = self.env['stock.picking.type']
        picking_type_id = picking_type_obj.search([('company_id','=',self.company_id.id),('sequence_code','=','TDB')])
        sequence_id = self.env['ir.sequence'].search([('prefix','=','TDB')])
        if not picking_type_id:
            vals={
                'name': 'To Deliveryboy',
                'sequence_code': 'TDB',
                'company_id':self.company_id.id,
                'code':'internal',
                'sequence_id': sequence_id.id if sequence_id else False,
                'warehouse_id':False
            }
            picking_type = picking_type_obj.sudo().create(vals)
