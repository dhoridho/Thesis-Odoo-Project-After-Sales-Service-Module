from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_complete_name = fields.Char("Location Complete Name", compute='_compute_location_name', store=True)
    warehouse_delivery_steps = fields.Selection(related='warehouse_id.delivery_steps')

    @api.onchange('location_id')
    def _compute_branch_by_parent_location(self):

        self.branch_id = self.location_id.warehouse_id.branch_id.id

    @api.depends('name', 'location_id.name')
    def _compute_location_name(self):
        for record in self:
            name = record.name
            current = record
            while current.location_id:
                current = current.location_id
                name = '%s/%s' % (current.name, name)
            record.location_complete_name = name

    # @api.model
    # def create(self, vals):
    #     res = super(StockLocation, self).create(vals)
    #     res.create_op_type()
    #     return res

    # def create_op_type(self):
    #     warehouse_id = self.env['stock.warehouse'].search([('code', '=', self.location_id.name),
    #                                                        ('company_id', '=', self.env.company.id)], limit=1)
    #     all_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
    #     for ware in all_warehouse:
    #         code = ware.code + '/'
    #         if self.location_id and code in self.location_id.display_name:
    #             warehouse_id = ware
    #     if warehouse_id:
    #         source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
    #         sequence1_vals = {
    #             'name': warehouse_id.name + ' ' + self.name_get()[0][1] + ' Sequence Internal IN stock_location.py OPERATION',
    #             'implementation': 'standard',
    #             'prefix': warehouse_id.code + '/INT/IN',
    #             'padding': 3,
    #             'number_increment': 1,
    #             'number_next_actual': 1,
    #             'company_id': self.company_id.id
    #         }
    #         sequence1_id = self.env['ir.sequence'].create(sequence1_vals)
    #         operation1_vals = {
    #             'name': 'Internal Transfer IN ',
    #             'sequence_code': 'INT/IN',
    #             'code': 'internal',
    #             'default_location_src_id': source_location_id,
    #             'default_location_dest_id': self.id,
    #             'warehouse_id': warehouse_id and warehouse_id.id or False,
    #             'sequence_id': sequence1_id.id,
    #             'is_transit': True,
    #             'company_id': self.company_id.id
    #         }
    #         in_operation_id = self.env['stock.picking.type'].create(operation1_vals)
    #         sequence2_vals = {
    #             'name': warehouse_id.name + ' ' + self.name_get()[0][1] + ' Sequence Internal OUT stock_location.py OPERATION',
    #             'implementation': 'standard',
    #             'prefix': warehouse_id.code + '/INT/OUT',
    #             'padding': 3,
    #             'number_increment': 1,
    #             'number_next_actual': 1,
    #             'company_id': self.company_id.id,
    #         }
    #         sequence2_id = self.env['ir.sequence'].create(sequence2_vals)
    #         operation2_vals = {
    #             'name': 'Internal Transit OUT',
    #             'sequence_code': 'INT/OUT',
    #             'code': 'internal',
    #             'default_location_src_id': self.id,
    #             'default_location_dest_id': source_location_id,
    #             'warehouse_id': warehouse_id and warehouse_id.id or False,
    #             'sequence_id': sequence2_id.id,
    #             'is_transit': True,
    #             'company_id': self.company_id.id,
    #         }
    #         out_operation_id = self.env['stock.picking.type'].create(operation2_vals)
    #     return True
