from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_material_request_approval_matrix = fields.Boolean(
        string="Material Request Approval Matrix")
    is_internal_transfer_approval_matrix = fields.Boolean(
        string="Interwarehouse Transfer Approval Matrix")
    internal_type = fields.Selection(
        [('with_transit',
          'Use Transit Location before deliver to Destination Location'),
         ('direct_transit', 'Deliver directly to Destination Location')],
        string="Interwarehouse Transfer",
        default="with_transit")
    is_stock_count_approval = fields.Boolean(
        string=" Stock Count Approval Matrix")
    is_product_usage_approval = fields.Boolean(
        string="Product Usage Approval Matrix")
    is_return_orders = fields.Boolean(
        string="Return Request",
        help=
        "Instead of directly click Return from Transfer Operation documents, User can use Return Requests form to apply a return request of a Purchase Order or a Sale Order"
    )
    return_type = fields.Selection(
        [('direct_return', 'Direct Return'),
         ('return_request_form', 'Return Request Form'),
         ('both', 'Direct Return & Return Request Form')],
        string='Return Type',
        default="direct_return")
    # is_product_barcode_labels = fields.Boolean(string='Product Barcode Labels')
    is_inventory_adjustment_with_value = fields.Boolean(
        string="Accounting Inventory Adjustment")
    putaway_max_capacity = fields.Boolean("Putaway on Max capacity")
    set_warehouse_sublevel = fields.Boolean("Location Removal Priority")
    warehouse_sublevel_zone = fields.Boolean("Zone")
    warehouse_sublevel_shelf = fields.Boolean("Shelf")
    warehouse_sublevel_rack = fields.Boolean("Rack")
    warehouse_sublevel_bin = fields.Boolean("Bin")
    group_is_three_dimension_warehouse = fields.Boolean(
        string="3-Dimension Warehouse & Location",
        implied_group=
        'equip3_inventory_accessright_setting.group_is_three_dimension_warehouse'
    )
    is_mbs_on_transfer_operations = fields.Boolean(
        string="Mobile Barcode Scanner on Transfer Operations")
    is_mbs_on_product_usage = fields.Boolean(
        string="Mobile Barcode Scanner on Product Usage")
    is_mbs_on_stock_count_and_inventory_adjustment = fields.Boolean(
        string="Mobile Barcode Scanner on Stock Count and Inventory Adjustment"
    )
    outgoing_routing_strategy = fields.Boolean(
        string="Outgoing Routing Strategy")
    sort_quants_by = fields.Selection(
        [('location_removal_priority', 'Location Removal Priority'),
         ('location_name', 'Location Name')],
        string="Sort quants by",
        default="location_removal_priority")
    routing_order = fields.Selection([('ascending', 'Ascending(A-Z)'),
                                      ('descending', 'Descending(Z-A)')],
                                     string="Routing Order",
                                     default="ascending")
    is_receiving_notes_approval_matrix = fields.Boolean(
        string=" Receiving Notes Approval Matrix")
    is_adj_picking = fields.Boolean(string="Adjustable Picking")
    is_delivery_order_approval_matrix = fields.Boolean(
        string=" Delivery Order Approval Matrix")
    brand_setting = fields.Selection(
        [('without', 'Without Brand'),
         ('optional', 'Optional Brand Selection'),
         ('mandatory', 'Mandatory Brand Selection')],
        default='optional')
    is_mbs_on_itr_location = fields.Boolean(
        string="Mobile Barcode Scanner Source & Destination Location on Internal Transfer",
        config_parameter='equip3_inventory_accessright_setting.is_mbs_on_itr_location')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            internal_type=ICP.get_param('internal_type', 'with_transit'),
            is_material_request_approval_matrix=ICP.get_param(
                'is_material_request_approval_matrix', False),
            is_internal_transfer_approval_matrix=ICP.get_param(
                'is_internal_transfer_approval_matrix', False),
            is_stock_count_approval=ICP.get_param('is_stock_count_approval',
                                                  False),
            is_product_usage_approval=ICP.get_param(
                'is_product_usage_approval', False),
            is_return_orders=ICP.get_param('is_return_orders', False),
            return_type=ICP.get_param('return_type', False),
            is_inventory_adjustment_with_value=ICP.get_param(
                'is_inventory_adjustment_with_value', False),
            # is_product_barcode_labels=ICP.get_param('is_product_barcode_labels', False),
            putaway_max_capacity=ICP.get_param('putaway_max_capacity', False),
            set_warehouse_sublevel=ICP.get_param('set_warehouse_sublevel',
                                                 False),
            warehouse_sublevel_zone=ICP.get_param('warehouse_sublevel_zone',
                                                  False),
            warehouse_sublevel_shelf=ICP.get_param('warehouse_sublevel_shelf',
                                                   False),
            warehouse_sublevel_rack=ICP.get_param('warehouse_sublevel_rack',
                                                  False),
            warehouse_sublevel_bin=ICP.get_param('warehouse_sublevel_bin',
                                                 False),
            group_is_three_dimension_warehouse=ICP.get_param(
                'group_is_three_dimension_warehouse', False),
            is_mbs_on_transfer_operations=ICP.get_param(
                'is_mbs_on_transfer_operations', False),
            is_mbs_on_product_usage=ICP.get_param('is_mbs_on_product_usage',
                                                  False),
            is_mbs_on_stock_count_and_inventory_adjustment=ICP.get_param(
                'is_mbs_on_stock_count_and_inventory_adjustment', False),
            outgoing_routing_strategy=ICP.get_param(
                'outgoing_routing_strategy', False),
            is_receiving_notes_approval_matrix=ICP.get_param(
                'is_receiving_notes_approval_matrix', False),
            sort_quants_by=ICP.get_param('sort_quants_by',
                                         'location_removal_priority'),
            routing_order=ICP.get_param('routing_order', 'ascending'),
            is_adj_picking=ICP.get_param('is_adj_picking'),
            is_delivery_order_approval_matrix=ICP.get_param(
                'is_delivery_order_approval_matrix', False),
            brand_setting=ICP.get_param('brand_setting', 'optional'),
        )
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        is_material_request_approval_matrix = self.is_material_request_approval_matrix
        is_internal_transfer_approval_matrix = self.is_internal_transfer_approval_matrix
        is_stock_count_approval = self.is_stock_count_approval
        is_product_usage_approval = self.is_product_usage_approval
        is_inventory_adjustment_with_value = self.is_inventory_adjustment_with_value
        is_return_orders = self.is_return_orders
        return_type = self.return_type
        putaway_max_capacity = self.putaway_max_capacity
        set_warehouse_sublevel = self.set_warehouse_sublevel
        warehouse_sublevel_zone = self.warehouse_sublevel_zone
        warehouse_sublevel_shelf = self.warehouse_sublevel_shelf
        warehouse_sublevel_rack = self.warehouse_sublevel_rack
        warehouse_sublevel_bin = self.warehouse_sublevel_bin
        group_is_three_dimension_warehouse = self.group_is_three_dimension_warehouse
        is_mbs_on_transfer_operations = self.is_mbs_on_transfer_operations
        is_mbs_on_product_usage = self.is_mbs_on_product_usage
        is_mbs_on_stock_count_and_inventory_adjustment = self.is_mbs_on_stock_count_and_inventory_adjustment
        outgoing_routing_strategy = self.outgoing_routing_strategy
        is_receiving_notes_approval_matrix = self.is_receiving_notes_approval_matrix
        is_adj_picking = self.is_adj_picking
        is_delivery_order_approval_matrix = self.is_delivery_order_approval_matrix
        brand_setting = self.brand_setting
        company = self.env['res.company'].browse(self.env.company.id)
        if company:
            company.write({'brand_setting': self.brand_setting})
            # if company.brand_setting == 'without':
            #     rec.product_brand_ids = [(5, 0, 0)]

        if not self.inventory:
            is_material_request_approval_matrix = False
            is_internal_transfer_approval_matrix = False
            is_stock_count_approval = False
            is_product_usage_approval = False
            is_inventory_adjustment_with_value = False
            is_return_orders = False
            return_type = False
            putaway_max_capacity = False
            group_is_three_dimension_warehouse = False
            is_mbs_on_transfer_operations = False
            is_mbs_on_product_usage = False
            is_mbs_on_stock_count_and_inventory_adjustment = False
            outgoing_routing_strategy = False
            is_receiving_notes_approval_matrix = False
            is_delivery_order_approval_matrix = False
            brand_setting = False

        if not self.accounting:
            is_inventory_adjustment_with_value = False

        ICP.set_param('is_material_request_approval_matrix',
                      is_material_request_approval_matrix)
        ICP.set_param('is_internal_transfer_approval_matrix',
                      is_internal_transfer_approval_matrix)
        ICP.set_param('is_stock_count_approval', is_stock_count_approval)
        ICP.set_param('is_product_usage_approval', is_product_usage_approval)
        ICP.set_param('internal_type', self.internal_type)
        ICP.set_param('sort_quants_by', self.sort_quants_by)
        ICP.set_param('routing_order', self.routing_order)
        ICP.set_param('is_return_orders', is_return_orders)
        ICP.set_param('return_type', return_type)
        ICP.set_param('is_inventory_adjustment_with_value',
                      is_inventory_adjustment_with_value)
        ICP.set_param('putaway_max_capacity', putaway_max_capacity)
        ICP.set_param('set_warehouse_sublevel', set_warehouse_sublevel)
        ICP.set_param('warehouse_sublevel_zone', warehouse_sublevel_zone)
        ICP.set_param('warehouse_sublevel_shelf', warehouse_sublevel_shelf)
        ICP.set_param('warehouse_sublevel_rack', warehouse_sublevel_rack)
        ICP.set_param('warehouse_sublevel_bin', warehouse_sublevel_bin)
        ICP.set_param('group_is_three_dimension_warehouse',
                      group_is_three_dimension_warehouse)
        ICP.set_param('is_mbs_on_transfer_operations',
                      is_mbs_on_transfer_operations)
        ICP.set_param('is_mbs_on_product_usage', is_mbs_on_product_usage)
        ICP.set_param('is_mbs_on_stock_count_and_inventory_adjustment',
                      is_mbs_on_stock_count_and_inventory_adjustment)
        ICP.set_param('outgoing_routing_strategy', outgoing_routing_strategy)
        ICP.set_param('is_receiving_notes_approval_matrix',
                      is_receiving_notes_approval_matrix)
        ICP.set_param('is_adj_picking', is_adj_picking)
        ICP.set_param('is_delivery_order_approval_matrix',
                      is_delivery_order_approval_matrix)
        ICP.set_param('brand_setting', brand_setting)

        # ICP.set_param('is_product_barcode_labels', self.is_product_barcode_labels)

        if self.internal_type == 'with_transit':
            self.env.ref('equip3_inventory_operation.menu_internal_transfer_in'
                         ).active = True
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_out'
            ).active = True
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_notes'
            ).active = True
        else:
            self.env.ref('equip3_inventory_operation.menu_internal_transfer_in'
                         ).active = False
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_out'
            ).active = False
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_notes'
            ).active = False

        # if self.is_return_orders:
        #     self.env.ref('dev_rma.manu_dev_rma_rma').active = True
        #     self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so').active = True
        # else:
        #     self.env.ref('dev_rma.manu_dev_rma_rma').active = False
        #     self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so').active = False

        if self.set_warehouse_sublevel:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_manage_wh_sublevel'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_manage_wh_sublevel'
            ).active = False
            self.warehouse_sublevel_zone = False
            self.warehouse_sublevel_shelf = False
            self.warehouse_sublevel_rack = False
            self.warehouse_sublevel_bin = False

        if self.warehouse_sublevel_zone:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_zone'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_zone'
            ).active = False

        if self.warehouse_sublevel_shelf:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_shelf'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_shelf'
            ).active = False

        if self.warehouse_sublevel_rack:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_rack'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_rack'
            ).active = False

        if self.warehouse_sublevel_bin:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_bin'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_wh_sublevel_bin'
            ).active = False

        if self.outgoing_routing_strategy:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_manage_wh_sublevel'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_manage_wh_sublevel'
            ).active = False
            location_rec = self.env['stock.location'].search([('usage', '=',
                                                               'internal')])
            for location in location_rec:
                location.removal_priority = 0
        if self.sort_quants_by == 'location_removal_priority':
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_manage_wh_sublevel'
            ).active = True
        else:
            self.env.ref(
                'equip3_inventory_accessright_setting.menu_manage_wh_sublevel'
            ).active = False
            location_rec = self.env['stock.location'].search([('usage', '=',
                                                               'internal')])
            for location in location_rec:
                location.removal_priority = 0

        if self.is_receiving_notes_approval_matrix:
            self.env.ref('equip3_inventory_operation.rn_approval_matrix_menu'
                         ).active = True
        else:
            self.env.ref('equip3_inventory_operation.rn_approval_matrix_menu'
                         ).active = False

        if self.is_delivery_order_approval_matrix:
            self.env.ref('equip3_inventory_operation.do_approval_matrix_menu'
                         ).active = True
        else:
            self.env.ref('equip3_inventory_operation.do_approval_matrix_menu'
                         ).active = False

        if self.return_type == 'return_request_form':
            self.env.ref('dev_rma.manu_dev_rma_rma').active = True
            self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so'
                         ).active = True

        if self.return_type == 'direct_return':
            self.env.ref('dev_rma.manu_dev_rma_rma').active = False
            self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so'
                         ).active = False

        if self.return_type == 'both':
            self.env.ref('dev_rma.manu_dev_rma_rma').active = True
            self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so'
                         ).active = True

        # if self.is_product_barcode_labels:
        #     self.env.ref('dynamic_barcode_labels.group_barcode_labels').hide = True
        # else:
        #     self.env.ref('dynamic_barcode_labels.group_barcode_labels').active = False

        # if self.return_type == 'return_request_form':
        #     self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so').active = True
        #     self.env.ref('dev_rma.manu_dev_rma_rma').active = True
        # elif self.return_type == 'both':
        #     self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so').active = True
        #     self.env.ref('dev_rma.manu_dev_rma_rma').active = True
        # else:
        #     self.env.ref('equip3_inventory_operation.menu_dev_rma_rma_main_so').active = False
        #     self.env.ref('dev_rma.manu_dev_rma_rma').active = False

        return res
