# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import Warning, ValidationError
from datetime import datetime, date, timedelta
import json


class InheritedInternalTransferWizardLine(models.TransientModel):
    _inherit = 'mr.internal_transfer_line'

    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', string="Section")
    variable = fields.Many2one('variable.template', string="Variable")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    construction_source_warehouse_domain = fields.Char(string='Worker', compute='_compute_construction_source_warehouse_domain')

    def _compute_construction_source_warehouse_domain(self):
        for rec in self:
            if rec.product_id:
                self.env.cr.execute(
                    """SELECT warehouse_id FROM stock_quant WHERE product_id = %s AND quantity > 0""",
                    (rec.product_id.id,))
                temp_warehouse_ids = self.env.cr.fetchall()
                warehouse_ids = list([x[0] for x in temp_warehouse_ids])
                if rec.project_scope or rec.section or rec.variable or rec.group_of_product:
                    if warehouse_ids:
                        rec.construction_source_warehouse_domain = json.dumps([('id', 'in', warehouse_ids), ('id', '!=', rec.dest_warehouse_id.id)])
                    else:
                        rec.construction_source_warehouse_domain = json.dumps([('id', 'in', [])])
                else:
                    rec.construction_source_warehouse_domain = json.dumps([('id', '!=', rec.dest_warehouse_id.id)])


class InheritedIntrawarehouseTransferLine(models.TransientModel):
    _inherit = 'intrawarehouse.transfer.line'

    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', string="Section")
    variable = fields.Many2one('variable.template', string="Variable")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')


class InheritedIntrawarehouseTransfer(models.TransientModel):
    _inherit = 'intrawarehouse.transfer'

    def default_intra_transfer_line(self):
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'material.request':
            material_request_id = self.env['material.request'].browse(self._context.get('active_ids'))
            intra_tra = []
            count = 1
            error_lines = []
            counter = 1
            for line in material_request_id.product_line:
                vals = {
                    'no': count,
                    'mr_id': line.material_request_id.id,
                    'project_scope': line.project_scope.id,
                    'section': line.section.id,
                    'variable': line.variable.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product.id,
                    'description': line.description,
                    'uom_id': line.product.uom_id.id,
                    'qty_transfer': line.quantity,
                    'mr_line_id': line.id,
                }
                intra_tra.append((0, 0, vals))
                count = count + 1
            return intra_tra
        else:
            material_request_line_ids = self.env['material.request.line'].browse(self._context.get('active_ids'))
            intra_tra = []
            count = 1
            error_lines = []
            counter = 1
            for line in material_request_line_ids:
                vals = {
                    'no': count,
                    'mr_id': line.material_request_id.id,
                    'project_scope': line.project_scope.id,
                    'section': line.section.id,
                    'variable': line.variable.id,
                    'group_of_product': line.group_of_product.id,
                    'product_id': line.product.id,
                    'description': line.description,
                    'uom_id': line.product.uom_id.id,
                    'qty_transfer': line.quantity,
                    'mr_line_id': line.id,
                }
                intra_tra.append((0, 0, vals))
                count = count + 1
            return intra_tra

    interawarehouse_transfer_ids = fields.One2many('intrawarehouse.transfer.line', 'intra_transfer_wizard_id',
                                                   default=default_intra_transfer_line)

    def create_intra_transfer(self):
        res = super(InheritedIntrawarehouseTransfer, self).create_intra_transfer()
        # for record in self:
        #     temp_data = []
        #     final_data = []
        #     for line in record.interawarehouse_transfer_ids:
        #         if {'source_loc_id': line.source_loc_id.id, 'dest_loc_id': line.dest_loc_id.id} in temp_data:
        #             filter_lines = list(filter(lambda r: r.get('source_loc_id') == line.source_loc_id.id and r.get(
        #                 'dest_loc_id') == line.dest_loc_id.id, final_data))
        #             if filter_lines:
        #                 filter_lines[0]['lines'].append({
        #                     'project_scope': line.project_scope.id,
        #                     'section': line.section.id,
        #                     'variable': line.variable.id,
        #                     'group_of_product': line.group_of_product.id,
        #                     'product_id': line.product_id.id,
        #                     'description': line.description,
        #                     'product_uom': line.uom_id.id,
        #                     'product_uom_qty': line.qty_transfer,
        #                     'mr_line_id': line.mr_line_id.id,
        #                 })
        #         else:
        #             temp_data.append({
        #                 'source_loc_id': line.source_loc_id.id,
        #                 'dest_loc_id': line.dest_loc_id.id
        #             })
        #             final_data.append({
        #                 'source_loc_id': line.source_loc_id.id,
        #                 'dest_loc_id': line.dest_loc_id.id,
        #                 'warehouse_id': line.warehouse_id,
        #                 'mr_id': line.mr_id,
        #                 'lines': [{
        #                     'project_scope': line.project_scope.id,
        #                     'section': line.section.id,
        #                     'variable': line.variable.id,
        #                     'group_of_product': line.group_of_product.id,
        #                     'product_id': line.product_id.id,
        #                     'description': line.description,
        #                     'product_uom': line.uom_id.id,
        #                     'mr_line_id': line.mr_line_id.id,
        #                     'product_uom_qty': line.qty_transfer,
        #                 }]
        #             })
        #     for data in final_data:
        #         vals = {
        #             'warehouse_id': data.get('warehouse_id').id,
        #             'picking_type_id': data.get('warehouse_id').int_type_id.id,
        #             'location_id': data.get('source_loc_id'),
        #             'location_dest_id': data.get('dest_loc_id'),
        #             'mr_id': data.get('mr_id').id,
        #             'origin': data.get('mr_id').name,
        #             'scheduled_date': data.get('mr_id').schedule_date,
        #             'is_interwarehouse_transfer': True,
        #             'branch_id': data.get('mr_id').branch_id.id,
        #             'move_ids_without_package': [(0, 0, {
        #                 'project_scope': line.get('project_scope'),
        #                 'section': line.get('section'),
        #                 # 'variable': line.get('variable'),
        #                 'group_of_product': line.get('group_of_product'),
        #                 'product_id': line.get('product_id'),
        #                 'mr_line_id': line.get('mr_line_id'),
        #                 'description_picking': line.get('description'),
        #                 'name': line.get('description'),
        #                 'product_uom_qty': line.get('product_uom_qty'),
        #                 'product_uom': line.get('product_uom'),
        #             }) for line in data.get('lines')]
        #         }
        #         stock_picking_id = self.env['stock.picking'].search([('mr_id', '=', data.get('mr_id').id),
        #                                                              ('is_interwarehouse_transfer', '=', True)],
        #                                                             order="create_date desc", limit=1)
        #         stock_picking_id.move_ids_without_package.unlink()
        #         stock_picking_id.write(vals)
        return res


class InheritedInternalTransferWizard(models.TransientModel):
    _inherit = 'mr.internal_transfer'

    def create_ir(self):
        res = super(InheritedInternalTransferWizard, self).create_ir()
        source_warehouse = []
        for line in self.ir_wizard_line:
            if line.source_warehouse_id.id not in source_warehouse:
                source_warehouse.append(line.source_warehouse_id.id)
            if not line.source_warehouse_id.id:
                raise ValidationError("Please Add Warehouse For Internal Transfer")
            # quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
            # if quantity > line.mr_line_id.quantity:
            #     raise ValidationError(_('You cannot create a ITR for %s with more quantity then you Requested.') %
            #                           (line.product_id.name))
        ir_id_list = []
        for loc in source_warehouse:
            ir_line = []
            source_location_id = self.env['stock.location'].search(
                [('warehouse_id', '=', loc), ('usage', '=', 'internal')], limit=1, order="id")
            mr_id = self.ir_wizard_line.mapped('mr_id')
            destination_location_id = self.env['stock.location'].search(
                [('warehouse_id', '=', mr_id.destination_warehouse_id.id), ('usage', '=', 'internal')], limit=1,
                order="id")
            for line in self.ir_wizard_line:
                if loc == line.source_warehouse_id.id:
                    vals = {
                        'project_scope': line.project_scope.id,
                        'section': line.section.id,
                        'variable': line.variable.id,
                        'group_of_product': line.group_of_product.id,
                        'product_id': line.product_id.id,
                        'uom': line.uom_id.id,
                        'qty': line.qty_transfer,
                        'scheduled_date': self.ir_wizard_line.mr_id.schedule_date,
                        'destination_location_id': destination_location_id.id,
                        'source_location_id': source_location_id.id,
                        'description': line.description or line.product_id.display_name,
                        'source_document': self.ir_wizard_line.mr_id.name,
                        'requested_by': self.ir_wizard_line.mr_id.requested_by.id,
                        'company_id': self.ir_wizard_line.mr_id.company_id.id,
                        'mr_line_id': line.mr_line_id.id,
                    }
                    ir_line.append((0, 0, vals))
                    warehouse_id = self.env['stock.warehouse'].search(
                        [('lot_stock_id', '=', self.ir_wizard_line.mr_id.destination_location_id.id)])
                    warehouse_id_source = self.env['stock.warehouse'].search(
                        [('lot_stock_id', '=', line.source_location.id)])

            # compute eexpiry date
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            itr_expiry_days = IrConfigParam.get_param('mr_expiry_days', 'before')
            itr_ex_period = IrConfigParam.get_param('ex_period', 0)
            # if self.scheduled_date:
            if itr_expiry_days == 'before':
                expiry_date = self.ir_wizard_line.mr_id.schedule_date - timedelta(days=int(itr_ex_period))
            else:
                expiry_date = self.ir_wizard_line.mr_id.schedule_date + timedelta(days=int(itr_ex_period))
            ir_line_id = self.env['internal.transfer'].search([('mr_id', '=', self.ir_wizard_line.mr_id.id), ],
                                                              order="create_date desc", limit=1)
            ir_line_id.product_line_ids.unlink()

            # Not optimal this is temporary workaround because of validation in super is deleted
            # for line in self.ir_wizard_line:
            #     quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
            #     if quantity > line.mr_line_id.quantity:
            #         raise ValidationError(_('You cannot create a ITR for %s with more quantity then you Requested.') %
            #                               (line.product_id.name))

            ir_line_id.write({'product_line_ids': ir_line,
                              'project': self.ir_wizard_line.mr_id.project.id,
                              'branch_id': self.ir_wizard_line.mr_id.branch_id.id,
                              'type_of_mr': self.ir_wizard_line.mr_id.type_of_mr,
                              'cost_sheet': self.ir_wizard_line.mr_id.job_cost_sheet.id,
                              'source_document': self.ir_wizard_line.mr_id.name,
                              'scheduled_date': self.ir_wizard_line.mr_id.schedule_date,
                              'expiry_date': expiry_date,
                              'source_location_id': source_location_id.id,
                              'analytic_account_group_ids': [(6, 0,
                                                              self.ir_wizard_line.mr_id.analytic_account_group_ids.ids)],
                              'destination_location_id': destination_location_id.id,
                              'source_warehouse_id': loc,
                              'destination_warehouse_id': self.ir_wizard_line.mr_id.destination_warehouse_id.id,
                              'is_from_itr_wizard': True,
                              })
            ir_line_id.write({'mr_id': [(4, self.ir_wizard_line.mr_id.id)]})
            ir_id_list.append(ir_line_id)
            ir_line_id.onchange_source_loction_id()
            ir_line_id.onchange_dest_loction_id()
            for line in ir_line_id.product_line_ids:
                line._onchange_group_of_product()
            count = 1
            ir_id_list.append(ir_line_id)
            for ir in ir_line_id.product_line_ids:
                ir.write({
                    'sequence': count,
                    'source_location_id': source_location_id.id,
                    'destination_location_id': destination_location_id.id
                })
                count += 1
                mr_lines_id = self.env['material.request.line'].search(
                    [('id', '=', ir.mr_line_id.id), ('product', '=', ir.product_id.id)])
                for rec in mr_lines_id:
                    rec.write({'ir_lines_ids': [(4, ir.id)]})

        return res
