from venv import create
from numpy import product
from odoo import api, fields, models, _
from odoo.exceptions import UserError, Warning, ValidationError

class CreateAssetWizard(models.TransientModel):
    _name = "create.asset.wizard"
    _description = "Create Asset Wizard"
    
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Inventory Name')
    create_asset_ids = fields.One2many('create.asset.wizard.line', 'create_asset_id', 'Create Asset Wizard Lines', readonly=False)
    
    @api.model
    def default_get(self, fields):
        res = super(CreateAssetWizard, self).default_get(fields)
        move_ids = self.env['stock.move'].search([('picking_id', '=', self.env.context['default_picking_id'])])
        fac_area = self.env['maintenance.facilities.area'].search([])[0]
        held_by_id = self.env['res.partner'].search([])[0]
        create_asset_ids = []
        for move in move_ids:
            for _ in range(int(move.product_uom_qty)):
                category = move.product_id.asset_control_category
                if move.product_id.type == 'asset':
                    if move.product_id.asset_entry_perqty:
                        qty = move.product_uom_qty
                        account_asset_ids = self.env['account.asset.asset'].search(
                            [('product_id', '=', move.product_id.id)],
                            order="id desc", limit=move.product_uom_qty).ids

                        parts_lines = []
                        for part in move.product_id.asset_parts_line:
                            for x in range(part.qty):
                                parts_lines.append((0, 0, {
                                    'asset_part_id': part.id,
                                    'sn': 0,
                                    'category_id': category,
                                }))
                        for i in range(int(qty)):
                            create_asset_ids.append((0, 0, {
                                'account_asset_id':account_asset_ids[i],
                                'product_id': move.product_id.id,
                                'asset_name': move.product_id.name,
                                'asset_type': move.product_id.type,
                                'asset_cat': category,
                                'fac_area': fac_area,
                                'held_by_id': held_by_id,
                                'part_sn_ids': parts_lines,
                                'asset_value': move.purchase_line_id.price_unit or 0.0
                            }))
                    else:
                        account_asset_id = self.env['account.asset.asset'].search([('product_id', '=', move.product_id.id)],
                                                                                order="id desc", limit=1)
                        parts_lines = []
                        for part in move.product_id.asset_parts_line:
                            for x in range(part.qty):
                                parts_lines.append((0, 0, {
                                    'asset_part_id': part.id,
                                    'sn': 0,
                                    'category_id': category,
                                }))
                        create_asset_ids.append((0, 0, {
                            'account_asset_id': account_asset_id.id,
                            'product_id': move.product_id.id,
                            'asset_name': move.product_id.name,
                            'asset_type': move.product_id.type,
                            'asset_cat': category,
                            'fac_area': fac_area,
                            'held_by_id': held_by_id,
                            'part_sn_ids': parts_lines,
                            'asset_value': move.purchase_line_id.price_unit or 0.0
                        }))
                # else:
                #     account_asset_id = self.env['account.asset.asset'].search([('product_id', '=', move.product_id.id)],
                #                                                             order="id desc", limit=1)
                #     for i in range(int(move.product_uom_qty)):
                #         create_asset_ids.append((0, 0, {
                #             'account_asset_id': account_asset_id.id,
                #             'product_id': move.product_id.id,
                #             'asset_name': move.product_id.name,
                #             'asset_type': move.product_id.type,
                #             'asset_cat': category,
                #             'fac_area': fac_area,
                #             'held_by_id': held_by_id,
                #             'part_sn_ids': [(0, 0, {
                #                     'asset_part_id': part.id,
                #                     'sn': 0,
                #                     }) for part in move.product_id.asset_parts_line],
                #         }))
        res['create_asset_ids'] = create_asset_ids
        return res
       
    # def create_asset(self):
    #     self._check_create_asset_ids()
    #     if self.create_asset_ids:
    #         self.inventory_id.is_asset_created = True
    #         equip = self.env['maintenance.equipment']
    #         try:
    #             for line in self.create_asset_ids:
    #                 asset_parts_ids = []
    #                 for parts in line.part_sn_ids:
    #                     asset_parts = self.env['maintenance.equipment'].create({
    #                         'name': parts.asset_part_id.name,
    #                         'serial_no': parts.sn,
    #                         'category_id': parts.category_id.id,
    #                         'branch_id': parts.parts_fill_id.branch_id.id,
    #                         'vehicle_checkbox': False,
    #                         'owner': parts.parts_fill_id.owner.id,
    #                         'fac_area': parts.parts_fill_id.fac_area.id,
    #                         'held_by_id': parts.parts_fill_id.held_by_id.id,
    #                     })
    #                     asset_parts_ids.append(asset_parts)
    #                 create_asset = equip.create({
    #                     'name': line.asset_name,
    #                     'category_id': line.asset_cat.id,
    #                     'owner' : line.owner.id,
    #                     'branch_id': line.branch_id.id,
    #                     'asset_value': line.account_asset_id.value,
    #                     'fac_area' : line.fac_area.id,
    #                     'serial_no': line.serial_number,
    #                     'effective_date': line.eff_date,
    #                     'vehicle_checkbox': True if line.asset_type == 'vehicle' else False,
    #                     'held_by_id': line.held_by_id.id,
    #                 })
    #                 if create_asset:
    #                     line.account_asset_id.equipment_id = create_asset.id
    #                     create_asset.account_asset_id.unlink()
    #                     create_asset.account_asset_id = line.account_asset_id.id
    #                     create_asset.vehicle_parts_ids = [(0, 0, {
    #                         'maintenance_equipment_id': create_asset.id,
    #                         'equipment_id': parts.id,
    #                         'serial_no': parts.serial_no,
    #                     }) for parts in asset_parts_ids]
    #             self.env['stock.picking'].browse(self.inventory_id.id).write({'is_asset_created': True})
    #         except Exception as e:
    #             # print("exception is occurred",e)
    #             raise Warning(e)
    #     return {'type': 'ir.actions.act_window_close'}
    def create_asset(self): 
        self._check_create_asset_ids()
        picking = self.picking_id
        picking.is_asset_created = True

        try:
            for line in self.create_asset_ids:
                asset_parts_ids = self._create_asset_parts(line)
                created_asset = self._create_main_asset(line, asset_parts_ids)

                if created_asset:
                    # Link the created asset with account asset
                    line.account_asset_id.equipment_id = created_asset.id
                    created_asset.account_asset_id = line.account_asset_id.id

            # Mark the picking as asset created
            picking.write({'is_asset_created': True})

        except Exception as e:
            raise UserError(f"An error occurred while creating assets: {e}")

        return {'type': 'ir.actions.act_window_close'}

    def _create_asset_parts(self, line):
        """Create asset parts for a given line."""
        asset_parts_ids = []
        MaintenanceEquipment = self.env['maintenance.equipment']

        for parts in line.part_sn_ids:
            part_vals = {
                'name': parts.asset_part_id.name,
                'serial_no': parts.sn,
                'category_id': parts.category_id.id,
                'branch_id': parts.parts_fill_id.branch_id.id,
                'vehicle_checkbox': False,
                'owner': parts.parts_fill_id.owner.id,
                'fac_area': parts.parts_fill_id.fac_area.id,
                'held_by_id': parts.parts_fill_id.held_by_id.id,
            }
            asset_part = MaintenanceEquipment.create(part_vals)
            asset_parts_ids.append(asset_part)

        return asset_parts_ids

    def _create_main_asset(self, line, asset_parts_ids):
        """Create the main asset and link vehicle parts."""
        MaintenanceEquipment = self.env['maintenance.equipment']
        
        asset_vals = {
            'name': line.asset_name,
            'category_id': line.asset_cat.id,
            'owner': line.owner.id,
            'branch_id': line.branch_id.id,
            'asset_value': line.asset_value or 0.0,
            'fac_area': line.fac_area.id,
            'serial_no': line.serial_number,
            'effective_date': line.eff_date,
            'vehicle_checkbox': line.asset_type == 'vehicle',
            'held_by_id': line.held_by_id.id,
            'product_template_id': line.product_id.product_tmpl_id.id,
        }
        created_asset = MaintenanceEquipment.create(asset_vals)

        if created_asset:
            created_asset.vehicle_parts_ids = [
                (0, 0, {
                    'maintenance_equipment_id': created_asset.id,
                    'equipment_id': part.id,
                    'serial_no': part.serial_no,
                }) for part in asset_parts_ids
            ]

        return created_asset

    def _check_create_asset_ids(self):
        # check if the account asset is set for each line
        for asset in self.create_asset_ids:
            if asset:
                account_asset_ids_1 = asset
                account_asset_ids_2 = list(set(account_asset_ids_1))
                if len(account_asset_ids_1) != len(account_asset_ids_2):
                    raise UserError(_('You cannot select the same account asset for multiple lines.'))
        # for line in self.create_asset_ids:
        #     for asset in self.create_asset_ids:
        #         if asset.account_asset_id.id == line.account_asset_id.id and asset.id != line.id:
        #             raise UserError(_('You cannot select the same account asset for multiple lines.'))
            
    
class CreateAssetWizardLine(models.TransientModel):
    _name = "create.asset.wizard.line"
    _description = "Create Asset Wizard Line"
    
    create_asset_id = fields.Many2one('create.asset.wizard', 'Create Asset Wizard')
    product_id = fields.Many2one('product.product', string='Product Name')
    asset_name = fields.Char(string='Asset Name')
    is_asset = fields.Boolean(string='Is Asset')
    account_asset_id = fields.Many2one('account.asset.asset', string='Asset Accounting')
    # related_account_asset_id = fields.Many2one('account.asset.asset', string='related Asset Account',store=True)
    # filter_account_asset_ids = fields.Many2many('account.asset.asset', string='Asset Account', compute='_compute_account_asset_filter')
    asset_type = fields.Selection([('asset', 'Asset'), ('vehicle', 'Vehicle')], string='Asset Type')
    serial_number = fields.Char(string='Serial Number', required=True)
    asset_cat = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    fac_area = fields.Many2one('maintenance.facilities.area', string='Facility Area', required=True)
    eff_date = fields.Date(string='Effective Date', default=fields.Date.today(), readonly=True)
    owner = fields.Many2one('res.partner', string='Owner', related='create_asset_id.picking_id.partner_id', readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch',related='create_asset_id.picking_id.branch_id', readonly=True)
    held_by_id = fields.Many2one(comodel_name='res.partner', string='Held By', required=True)
    part_sn_ids = fields.One2many(comodel_name='parts.sn.ids', inverse_name='parts_fill_id', string='Parts')
    asset_value = fields.Float(string='Asset Value')
    # @api.depends('product_id')
    # def _compute_is_asset(self):
    #     before_asset_ids = []
    #     for line in self:
    #         if line.product_id.type == 'asset':
    #             product_name = line.product_id.name
    #             account_asset_id = self.env['account.asset.asset'].search(
    #                 [('name', '=', product_name)], order="id desc")
    #             for rec in account_asset_id:
    #                 if line.related_account_asset_id != rec and rec not in before_asset_ids:
    #                     line.related_account_asset_id = rec
    #                     before_asset_ids.append(rec)
    #                     break
    #
    #     for line in self:
    #         if line.product_id.type == 'asset':
    #             line.is_asset = True
    #         else:
    #             line.is_asset = False
    #
    # @api.depends('account_asset_id')
    # def _compute_account_asset_filter(self):
    #     for line in self:
    #         data_ids = []
    #         account_asset_ids = self.env['account.asset.asset'].search([('equipment_id', '=', False)])
    #         for account_asset_id in account_asset_ids:
    #             data_ids.append(account_asset_id.id)
    #
    #         line.filter_account_asset_ids = [(6, 0, data_ids)]
class PartsSnIds(models.TransientModel):
    _name = "parts.sn.ids"
    _description = "Parts Serial Number IDs"
    _rec_name = 'asset_part_id'

    parts_fill_id = fields.Many2one('create.asset.wizard.line', string='Parts Fill', store=True)
    asset_part_id = fields.Many2one(comodel_name='asset.parts.line', string='Part', store=True)
    sn = fields.Char(string='Parts Serial Number', store=True)
    category_id = fields.Many2one(comodel_name='maintenance.equipment.category', string='Category')

    @api.onchange('sn')
    def onchange_serial_number(self):
        parts = self.env['vehicle.parts'].sudo().search([('maintenance_equipment_id', '!=', False), ('equipment_id', '!=', False)]).mapped('equipment_id')
        if not self.sn:
            return
        
        existing_sn_parts = self.env['maintenance.equipment'].sudo().search([('serial_no', '=', self.sn), ('id', 'in', parts.ids)], limit=1)
        if existing_sn_parts:
            existing_part = self.env['vehicle.parts'].sudo().search([('equipment_id', '=', existing_sn_parts.id)], limit=1)
            raise ValidationError(_(f'Serial Number {self.sn} is already used in [{existing_part.maintenance_equipment_id.serial_no}]{existing_part.maintenance_equipment_id.name} within part of [{existing_sn_parts.serial_no}]{existing_sn_parts.name}'))
        
        existing_sn_parent = self.env['maintenance.equipment'].sudo().search([('serial_no', '=', self.sn), ('id', 'not in', parts.ids)], limit=1)
        if existing_sn_parent:
            raise ValidationError(_(f'Serial Number {self.sn} is already used in {existing_sn_parent.name}'))