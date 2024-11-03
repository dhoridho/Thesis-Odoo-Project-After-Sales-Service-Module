from odoo import api, fields, models, _
from odoo.http import request


class Warehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char('Warehouse', index=True, required=True, default="")
    code = fields.Char('Short Name', required=True, size=5, help="Short name used to identify your warehouse")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company,
        index=True, readonly=True, required=True,
        help='The company is automatically set from your user preferences.')
    branch_id = fields.Many2one('res.branch', default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)],)
    lot_scrap_id = fields.Many2one(
        'stock.location', 'Location Scrap',
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
        required=True, check_company=True)
    lot_expired_id = fields.Many2one(
        'stock.location', 'Location Expired Stock',
        domain="[('company_id', 'in', [company_id, False])]",
        check_company=True,)
    street = fields.Char("Street")
    street2 = fields.Char("street2")
    zip = fields.Char("Zip")
    city = fields.Char("City")
    state_id = fields.Many2one('res.country.state', string="State", domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string="Country")
    phone = fields.Char("Telephone No")
    responsible_users = fields.Many2many("res.users", "stock_warehouse_res_users_rel", "warehouse_id" ,"user_id", "Responsible Users")
    planimetry_image = fields.Binary(string='Planimetry Image',help="Images must be uploaded if you want to set 3D Warehouse Overview")

    # @api.model
    # def update_value_branch(self):
    #     warehouse = self.env['stock.warehouse'].search([])
    #     branch = self.env['res.users'].search([('id', '=', self.env.user.id)])
    #     for rec in warehouse:
    #         if not rec.branch_id:
    #             rec.branch_id = branch.branch_id.id
    #             print("➡ rec.branch_id :", rec.branch_id)
    
    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Warehouses'),
            'template': '/equip3_inventory_masterdata/static/src/xls/warehouse_template.xlsx'
        }]


    def action_open_stock_locations(self):
        action = self.env.ref('stock.action_location_form').read()[0]
        action['domain'] = [('warehouse_id', '=', self.id)]
        return action

    @api.model
    def create(self, vals):
        if vals.get('company_id'):
            company_name = self.env['res.company'].browse(vals.get('company_id')).name
            if vals.get('name') == company_name:
                vals.update({'code': self.env['res.company'].browse(vals.get('company_id')).company_code})

        res = super(Warehouse, self).create(vals)
        res.create_location_expired_stock()
        res.transit_operation_types()
        res.set_responsible_users()
        return res


    def create_location_expired_stock(self):
        for record in self:
            loc_id = self.env['stock.location'].search([('name','=',record.code), ('company_id', '=', record.company_id.id)], limit=1)
            operation_types = self.env['stock.picking.type'].search([('warehouse_id', '=', record.id)])
            for op_type in operation_types:
                op_type.sequence_id.padding = 3
                if 'month' not in op_type.sequence_id.prefix:
                    op_type.sequence_id.prefix += '/%(y)s/%(month)s/%(day)s/'
            stock_loc = self.env['stock.location'].search([('company_id', '=', record.company_id.id)])
            for loc in stock_loc:
                if loc.location_id.name == record.code:
                    if loc.name == 'Stock':
                        source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
                        sequence4_vals = {
                            'name': record.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal IN',
                            'implementation': 'standard',
                            'prefix': loc.warehouse_id.code + '/INT/IN',
                            'padding': 3,
                            'number_increment': 1,
                            'number_next_actual': 1,
                            'company_id': record.company_id.id,
                        }
                        sequence4_id = self.env['ir.sequence'].create(sequence4_vals)
                        operation4_vals = {
                            'name': 'Internal Transfer IN ',
                            'sequence_code': 'INT/IN',
                            'code': 'internal',
                            'default_location_src_id': source_location_id,
                            'default_location_dest_id': loc.id,
                            'warehouse_id': record.id or False,
                            'sequence_id': sequence4_id.id,
                            'is_transit': True,
                            'company_id': record.company_id.id,
                            'display_name': loc.name_get()[0][1] + 'Internal Transfer IN',
                        }
                        in_operation_id = self.env['stock.picking.type'].create(operation4_vals)
                        # print('ipid',in_operation_id)
                        sequence5_vals = {
                            'name': record.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal OUT',
                            'implementation': 'standard',
                            'prefix': loc.warehouse_id.code + '/INT/OUT',
                            'padding': 5,
                            'number_increment': 1,
                            'number_next_actual': 1,
                            'company_id': record.company_id.id,
                        }
                        sequence5_id = self.env['ir.sequence'].create(sequence5_vals)
                        operation5_vals = {
                            'name': 'Internal Transit OUT',
                            'sequence_code': 'INT/OUT',
                            'code': 'internal',
                            'default_location_src_id': loc.id,
                            'default_location_dest_id': source_location_id,
                            'warehouse_id': record.id or False,
                            'sequence_id': sequence5_id.id,
                            'is_transit': True,
                            'company_id': record.company_id.id,
                            'display_name': loc.name_get()[0][1] + 'Internal Transfer IN',
                        }
                        out_operation_id = self.env['stock.picking.type'].create(operation5_vals)
                        # print('opid', out_operation_id)
            loc_vals_expired = {'name': 'Expired Stock', 'usage': 'internal',
                              'location_id': loc_id.id , 'company_id': record.company_id.id, 'is_expired_stock_location': True}
            expired_id = self.env['stock.location'].create(loc_vals_expired)
            record.write({'lot_expired_id': expired_id.id})

    def transit_operation_types(self):
        stock_loc = self.env['stock.location'].search([('company_id', '=', self.env.company.id)])
        for record in self:
            for loc in stock_loc:
                if loc.location_id.name == record.code:
                    op_type = self.env['stock.picking.type'].search([('warehouse_id','=', record.id), ('company_id', '=', record.company_id.id)])
                    pz = False
                    input = False
                    output = False
                    qc = False
                    for type in op_type:
                        if 'Input' in type.sequence_id.name:
                            input = True
                        if 'Output' in type.sequence_id.name:
                            output = True
                        if 'Packing Zone' in type.sequence_id.name:
                            pz = True
                        if 'Quality Control' in type.sequence_id.name:
                            qc = True
                    if (loc.name == 'Input' and input == False) or (loc.name == 'Output' and output == False) or (loc.name == 'Packing Zone' and pz == False) or (loc.name == 'Quality Control' and qc == False):
                    # if loc.name == 'Input' or loc.name == 'Output' or loc.name == 'Packing Zone' or loc.name == 'Quality Control':
                        source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
                        sequence_in_vals = {
                            'name': record.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal IN',
                            'implementation': 'standard',
                            'prefix': loc.name_get()[0][1] + '/INT/IN',
                            'padding': 3,
                            'number_increment': 1,
                            'number_next_actual': 1,
                        }
                        sequence_in_id = self.env['ir.sequence'].create(sequence_in_vals)
                        operation_in_vals = {
                            'name': 'Internal Transfer IN',
                            'sequence_code': 'INT/IN',
                            'code': 'internal',
                            'default_location_src_id': source_location_id,
                            'default_location_dest_id': loc.id,
                            'warehouse_id': record.id or False,
                            'sequence_id': sequence_in_id.id,
                            'is_transit': True,
                            # 'display_name': loc.name_get()[0][1] + 'Internal Transfer IN',
                        }
                        in_operation_id = self.env['stock.picking.type'].create(operation_in_vals)
                        # in_operation_id.display_name = loc.name_get()[0][1] + 'Internal Transfer OUT'
                        # print('ipid',in_operation_id)
                        sequence_out_vals = {
                            'name': record.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal OUT',
                            'implementation': 'standard',
                            'prefix': loc.name_get()[0][1] + '/INT/OUT',
                            'padding': 5,
                            'number_increment': 1,
                            'number_next_actual': 1,
                        }
                        sequence_out_id = self.env['ir.sequence'].create(sequence_out_vals)
                        operation_in_vals = {
                            'name': 'Internal Transit OUT',
                            'sequence_code': 'INT/OUT',
                            'code': 'internal',
                            'default_location_src_id': loc.id,
                            'default_location_dest_id': source_location_id,
                            'warehouse_id': record.id or False,
                            'sequence_id': sequence_out_id.id,
                            'is_transit': True,
                            # 'display_name': loc.name_get()[0][1] + 'Internal Transfer OUT',
                        }
                        out_operation_id = self.env['stock.picking.type'].create(operation_in_vals)
                        out_operation_id.display_name = loc.name_get()[0][1] + 'Internal Transfer OUT'
                        # print('odn',out_operation_id.display_name)

    def write(self, vals):
        res = super(Warehouse, self).write(vals)
        for record in self:
            location_id = self.env['stock.location'].search([('warehouse_id','=', record.id)])
            for x in location_id:
                x.branch_id = record.branch_id
            if record.reception_steps == 'three_steps' and record.delivery_steps == 'pick_pack_ship':
                stock_loc = record.env['stock.location'].search([])
                for loc in stock_loc:
                    if loc.location_id.name == record.code:
                        op_type = record.env['stock.picking.type'].search([('warehouse_id','=', record.id)])
                        pz = False
                        input = False
                        output = False
                        qc = False
                        for type in op_type:
                            if 'Input' in type.sequence_id.name:
                                input = True
                            if 'Output' in type.sequence_id.name:
                                output = True
                            if 'Packing Zone' in type.sequence_id.name:
                                pz = True
                            if 'Quality Control' in type.sequence_id.name:
                                qc = True
                        if (loc.name == 'Input' and input == False) or (loc.name == 'Output' and output == False) or (loc.name == 'Packing Zone' and pz == False) or (loc.name == 'Quality Control' and qc == False):
                            source_location_id = record.env.ref('equip3_inventory_masterdata.location_transit').id
                            sequence_in_vals = {
                                'name': record.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal IN',
                                'implementation': 'standard',
                                'prefix': loc.name_get()[0][1] + '/INT/IN',
                                'padding': 3,
                                'number_increment': 1,
                                'number_next_actual': 1,
                            }
                            sequence_in_id = record.env['ir.sequence'].create(sequence_in_vals)
                            operation_in_vals = {
                                'name': 'Internal Transfer IN',
                                'sequence_code': 'INT/IN',
                                'code': 'internal',
                                'default_location_src_id': source_location_id,
                                'default_location_dest_id': loc.id,
                                'warehouse_id': record.id or False,
                                'sequence_id': sequence_in_id.id,
                                'is_transit': True,
                                # 'display_name': loc.name_get()[0][1] + 'Internal Transfer IN',
                            }
                            in_operation_id = record.env['stock.picking.type'].create(operation_in_vals)
                            # in_operation_id.display_name = loc.name_get()[0][1] + 'Internal Transfer OUT'
                            # print('ipid',in_operation_id)
                            sequence_out_vals = {
                                'name': record.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal OUT',
                                'implementation': 'standard',
                                'prefix': loc.name_get()[0][1] + '/INT/OUT',
                                'padding': 5,
                                'number_increment': 1,
                                'number_next_actual': 1,
                            }
                            sequence_out_id = record.env['ir.sequence'].create(sequence_out_vals)
                            operation_in_vals = {
                                'name': 'Internal Transit OUT',
                                'sequence_code': 'INT/OUT',
                                'code': 'internal',
                                'default_location_src_id': loc.id,
                                'default_location_dest_id': source_location_id,
                                'warehouse_id': record.id or False,
                                'sequence_id': sequence_out_id.id,
                                'is_transit': True,
                                # 'display_name': loc.name_get()[0][1] + 'Internal Transfer OUT',
                            }
                            out_operation_id = record.env['stock.picking.type'].create(operation_in_vals)
                            out_operation_id.display_name = loc.name_get()[0][1] + 'Internal Transfer OUT'

    @api.onchange("branch_id")
    def _onchange_branch_id(self):
        if self.branch_id:
            self.street = self.branch_id.street
            self.street2 = self.branch_id.street_2
            self.zip = self.branch_id.zip_code
            self.city = self.branch_id.city
            self.state_id = self.branch_id.state_id
            self.country_id = self.branch_id.country_id
        else:
            self.street = self.company_id.street
            self.street2 = self.company_id.street2
            self.zip = self.company_id.zip
            self.city = self.company_id.city
            self.state_id = self.company_id.state_id
            self.country_id = self.company_id.country_id


    # @api.model
    # def create_expired_stock_location(self):
    #     chk_installed1 = self.env['ir.module.module'].search([('name', '=', 'equip3_inventory_masterdata')])
    #     if chk_installed1.state == 'to upgrade' or chk_installed1.state == 'to install':
    #         warehouse_id = self.env['stock.warehouse'].search([])
    #         stock_location = self.env['stock.location'].search([])
    #         for warehouse in warehouse_id:
    #             # print('....in.....', warehouse.lot_expired_id.id )
    #             if warehouse.lot_expired_id.id == False:
    #                 # print('name', warehouse.name)
    #                 for loc in stock_location:
    #                     if loc.location_id.name == warehouse.code:
    #                         if loc.is_expired_stock_location or loc.name == 'Expired Stock':
    #                             warehouse.lot_expired_id = loc.id
    #                         else:
    #                             # print('com',loc.company_id.name)
    #                             loc_vals_expired = {'name': 'Expired Stock', 'usage': 'internal', 'company_id': loc.company_id.id,
    #                                                 'location_id': loc.location_id.id , 'is_expired_stock_location': True}
    #                             expired_id = self.env['stock.location'].create(loc_vals_expired)
    #                             # print('ex_id',expired_id)
    #                             self.write({'lot_expired_id': expired_id.id})
    #                             warehouse.lot_expired_id = expired_id.id
    #                             source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
    #                             sequence1_vals = {
    #                                 'name': warehouse.name + ' ' + expired_id.name_get()[0][1] + ' Sequence Internal IN',
    #                                 'implementation': 'standard',
    #                                 'prefix': expired_id.name_get()[0][1] + '/INT/IN',
    #                                 'padding': 3,
    #                                 'number_increment': 1,
    #                                 'number_next_actual': 1,
    #                                 'company_id': expired_id.company_id.id
    #                             }
    #                             sequence1_id = self.env['ir.sequence'].create(sequence1_vals)
    #                             operation1_vals = {
    #                                 'name': 'Internal Transfer IN ',
    #                                 'sequence_code': 'INT/IN',
    #                                 'code': 'internal',
    #                                 'default_location_src_id': source_location_id,
    #                                 'default_location_dest_id': expired_id.id,
    #                                 'warehouse_id': warehouse and warehouse.id or False,
    #                                 'sequence_id': sequence1_id.id,
    #                                 'is_transit': True,
    #                                 'company_id': expired_id.company_id.id
    #                             }
    #                             in_operation_id = self.env['stock.picking.type'].create(operation1_vals)
    #                             sequence2_vals = {
    #                                 'name': warehouse.name + ' ' + expired_id.name_get()[0][1] + ' Sequence Internal OUT',
    #                                 'implementation': 'standard',
    #                                 'prefix': expired_id.name_get()[0][1] + '/INT/OUT',
    #                                 'padding': 3,
    #                                 'number_increment': 1,
    #                                 'number_next_actual': 1,
    #                                 'company_id': expired_id.company_id.id,
    #                             }
    #                             sequence2_id = self.env['ir.sequence'].create(sequence2_vals)
    #                             operation2_vals = {
    #                                 'name': 'Internal Transit OUT',
    #                                 'sequence_code': 'INT/OUT',
    #                                 'code': 'internal',
    #                                 'default_location_src_id': expired_id.id,
    #                                 'default_location_dest_id': source_location_id,
    #                                 'warehouse_id': warehouse and warehouse.id or False,
    #                                 'sequence_id': sequence2_id.id,
    #                                 'is_transit': True,
    #                                 'company_id': expired_id.company_id.id,
    #                             }
    #                             out_operation_id = self.env['stock.picking.type'].create(operation2_vals)
    #                             break


    def set_responsible_users(self):
        responsible_users = self.responsible_users
        self.location_responsible_users(self.view_location_id, responsible_users)
        self.location_responsible_users(self.lot_expired_id, responsible_users)
        self.location_responsible_users(self.lot_scrap_id, responsible_users)
        self.location_responsible_users(self.lot_stock_id, responsible_users)
        self.location_responsible_users(self.pbm_loc_id, responsible_users)
        self.location_responsible_users(self.sam_loc_id, responsible_users)
        self.location_responsible_users(self.wh_input_stock_loc_id, responsible_users)
        self.location_responsible_users(self.wh_output_stock_loc_id, responsible_users)
        self.location_responsible_users(self.wh_pack_stock_loc_id, responsible_users)
        self.location_responsible_users(self.wh_qc_stock_loc_id, responsible_users)

    def location_responsible_users(self, location, responsible_users):
        child_location = True
        while child_location:
            location.responsible_users = responsible_users
            for rec in location.child_ids:
                if not rec.child_ids:
                    rec.responsible_users = responsible_users
                    child_location = False
                else:
                    self.location_responsible_users(rec, responsible_users)
            child_location = False
