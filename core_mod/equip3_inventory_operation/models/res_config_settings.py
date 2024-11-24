
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    internal_type = fields.Selection([('with_transit', 'Use Transit Location before deliver to Destination Location'), (
        'direct_transit', 'Deliver directly to Destination Location')], string="Interwarehouse Transfer", default="with_transit")
    ex_period = fields.Integer(string="Interwarehouse Transfer Request Expiry",
                               help="The Expiry Date field on the Internal Transfer Request form will automatically be filled with the date and time based on the day period you fill in here.", default=30)
    material_request = fields.Integer(
        string="Material Request Expiry", default=30)
    is_product_service_operation = fields.Boolean(
        string="Product Service Operation", help="When Active, All Service Type Products Automatically Will Create A Receiving Note After Confirming A Purchase Or Delivery Order After Confirming A Sale. You Also Can Set Wheter The Product Will Create Operation Or Not On Each Product Template", default=False)
    is_product_service_operation_delivery = fields.Boolean(
        string="Product Service Operation Delivery", help="When Active, All Service Type Products Automatically Will Create A Delivery Order After Confirming A Sale. You Also Can Set Wheter The Product Will Create Operation Or Not On Each Product Template", default=False)
    is_product_service_operation_receiving = fields.Boolean(
        string="Product Service Operation Receiving", help="When Active, All Service Type Products Automatically Will Create A Receiving Note After Confirming A Purchase. You Also Can Set Wheter The Product Will Create Operation Or Not On Each Product Template", default=False)
    mr_expiry_days = fields.Selection(
        [('before', 'Before'), ('after', 'After')], default="after")
    itr_expiry_days = fields.Selection(
        [('before', 'Before'), ('after', 'After')], default="after")
    is_return_limit_policy = fields.Boolean(
        "Return Limit Policy", config_parameter="is_return_limit_policy")
    return_policy_days = fields.Integer(
        "Return Policy Days", config_parameter="return_policy_days")
    is_display_warehouse_address = fields.Boolean(
        "Display Warehouse Address on Delivery Slip")
    is_warehouse_shipments = fields.Boolean(
        string="Warehouse Shipments", store=True)
    qty_can_minus = fields.Boolean(
        string="Lock Transaction When Product Quantity is below 0", store=True)
    interwarehouse_transfer_journal = fields.Boolean(string='Interwarehouse Transfer Journal')
    measure_for_packaging_config = fields.Boolean(string="Measure For Packaging Config")
    
    # unused field
    product_packaging_config = fields.Boolean(string="Product Packaging Config")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'internal_type': IrConfigParam.get_param('internal_type', "with_transit"),
            'ex_period': int(IrConfigParam.get_param('ex_period', 30)),
            'material_request': int(IrConfigParam.get_param('material_request', 30)),
            'is_product_service_operation': IrConfigParam.get_param('is_product_service_operation', False),
            'is_product_service_operation_delivery': IrConfigParam.get_param('is_product_service_operation_delivery', False),
            'is_product_service_operation_receiving': IrConfigParam.get_param('is_product_service_operation_receiving', False),
            'mr_expiry_days': IrConfigParam.get_param('mr_expiry_days', 'before'),
            'itr_expiry_days': IrConfigParam.get_param('itr_expiry_days', 'before'),
            'is_display_warehouse_address': IrConfigParam.get_param('is_display_warehouse_address', False),
            'manufacturing': IrConfigParam.get_param('manufacturing', False),
            'is_warehouse_shipments': IrConfigParam.get_param('is_warehouse_shipments', False),
            'qty_can_minus': IrConfigParam.get_param('qty_can_minus', False),
            'interwarehouse_transfer_journal': IrConfigParam.get_param('interwarehouse_transfer_journal'),
            'measure_for_packaging_config': IrConfigParam.get_param('measure_for_packaging_config', False),
            # 'product_packaging_config': IrConfigParam.get_param('product_packaging_config', False),
        })
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        IrConfigParam.set_param('internal_type', self.internal_type)
        IrConfigParam.set_param('ex_period', self.ex_period)
        IrConfigParam.set_param('material_request', self.material_request)
        IrConfigParam.set_param('manufacturing', self.manufacturing)
        IrConfigParam.set_param(
            'is_product_service_operation', self.is_product_service_operation)
        IrConfigParam.set_param(
            'is_product_service_operation_delivery', self.is_product_service_operation_delivery)
        IrConfigParam.set_param(
            'is_product_service_operation_receiving', self.is_product_service_operation_receiving)
        IrConfigParam.set_param('mr_expiry_days', self.mr_expiry_days)
        IrConfigParam.set_param('itr_expiry_days', self.itr_expiry_days)
        IrConfigParam.set_param('interwarehouse_transfer_journal', self.interwarehouse_transfer_journal)
        IrConfigParam.set_param(
            'is_display_warehouse_address', self.is_display_warehouse_address)
        IrConfigParam.set_param('is_warehouse_shipments',
                                self.is_warehouse_shipments)
        IrConfigParam.set_param('qty_can_minus', self.qty_can_minus)
        IrConfigParam.set_param('measure_for_packaging_config', self.measure_for_packaging_config)
        data_id = self.env['ir.model.data'].xmlid_to_res_id(
            'equip3_inventory_operation.group_warehouse_shipments')
        res_group = self.env['res.groups'].browse([data_id])
        internal_users = self.env['res.users'].search([('active', '=', True)])
        for rec in internal_users:
            if self.is_warehouse_shipments:
                self.env.ref(
                    'equip3_inventory_operation.shipment_logistic_parent').active = True
                self.env.ref(
                    'equip3_inventory_operation.stock_picking_pick_child').active = True
                self.env.ref(
                    'equip3_inventory_operation.stock_picking_pack_child').active = True
                self.env.ref(
                    'equip3_inventory_operation.stock_picking_delivery_child').active = True

                if rec.has_group("base.group_user"):
                    rec.write({"groups_id": [(4, res_group.id)]})
            else:
                self.env.ref(
                    'equip3_inventory_operation.shipment_logistic_parent').active = False
                self.env.ref(
                    'equip3_inventory_operation.stock_picking_pick_child').active = False
                self.env.ref(
                    'equip3_inventory_operation.stock_picking_pack_child').active = False
                self.env.ref(
                    'equip3_inventory_operation.stock_picking_delivery_child').active = False

                if rec.has_group("base.group_user"):
                    rec.write({"groups_id": [(3, res_group.id)]})

        if self.internal_type == 'with_transit':
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_in').active = True
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_out').active = True
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_notes').active = False
        else:
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_in').active = False
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_out').active = False
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_notes').active = True

        product_template_ids = self.env['product.template'].search(
            [('type', '=', 'service')])
        product_ids = self.env['product.product'].search(
            [('type', '=', 'service')])

        if self.is_product_service_operation_delivery:
            for template in product_template_ids:
                template.write({'is_product_service_operation_delivery': True})
            for product in product_ids:
                product.write({'is_product_service_operation_delivery': True})
        else:
            for template in product_template_ids:
                template.write(
                    {'is_product_service_operation_delivery': False})
            for product in product_ids:
                product.write({'is_product_service_operation_delivery': False})

        if self.is_product_service_operation_receiving:
            for template in product_template_ids:
                template.write(
                    {'is_product_service_operation_receiving': True})
            for product in product_ids:
                product.write({'is_product_service_operation_receiving': True})
        else:
            for template in product_template_ids:
                template.write(
                    {'is_product_service_operation_receiving': False})
            for product in product_ids:
                product.write(
                    {'is_product_service_operation_receiving': False})
                
        if self.measure_for_packaging_config:
            self.env.ref(
                    'equip3_inventory_operation.measure_for_packaging_menu').active = True
        else:
            self.env.ref(
                    'equip3_inventory_operation.measure_for_packaging_menu').active = False
        
        # if self.product_packaging_config:
        #     self.env.ref(
        #             'stock.menu_product_packagings').active = True
        # else:
        #     self.env.ref(
        #             'stock.menu_product_packagings').active = False
        return res

    @api.onchange("is_return_limit_policy")
    def _onchange_is_return_limit_policy(self):
        self.return_policy_days = self.is_return_limit_policy and self.return_policy_days or 0
