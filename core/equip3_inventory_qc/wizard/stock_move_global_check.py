# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime
import json

class StockMoveQCWizard(models.TransientModel):
    _inherit = 'sh.stock.move.global.check'

    image_128 = fields.Image('Image', max_width=128, max_height=128)
    type_of_qc = fields.Selection(related='sh_quality_point_id.type_of_qc', string="QC Type")
    quantitative_line_ids = fields.One2many('wiz.qc.quantitative.lines', 'wiz_line_id', string="Quantitative Lines")
    qualitative_line_ids = fields.One2many('wiz.qc.qualitative.lines', 'wiz_line_id', string="Qualitative Lines")
    is_result = fields.Boolean(string="Is Result")
    is_all_pass = fields.Boolean(string="Is All Passed")
    is_from_recheck_line = fields.Boolean(string='Is From Recheck Line')
    recheck_max_number = fields.Integer(string="Maximum Number Of Test")
    is_recheck = fields.Boolean(string="is Rechecked")
    quality_check_id = fields.Many2one('sh.quality.check', string="Quality Checks")
    need_grade = fields.Boolean(string='Need Grade')
    product_grade_id = fields.Many2one(comodel_name='product.product', string='Product Grade')
    product_grade_id_domain = fields.Char(string='Product Grade Domain', compute="_compute_product_grade_id_domain")
    is_quality_point_grade = fields.Boolean(string='Is Quality Point Grade', default=False)
    

    @api.depends('sh_quality_point_id')    
    def _compute_product_grade_id_domain(self):
        # product_grade_ids = self.sh_quality_point_id.product_grade_ids.filtered(lambda x: x.id != self.product_id.id and x.product_tmpl_id.id == self.product_id.product_tmpl_id.id)
        product_grade_ids = self.sh_quality_point_id.product_grade_ids.filtered(lambda x: x.product_tmpl_id.id == self.product_id.product_tmpl_id.id)
        self.product_grade_id_domain = json.dumps([('id', 'in', product_grade_ids.ids)])

    @api.model
    def default_get(self, fields):
        res = super(StockMoveQCWizard, self).default_get(fields)
        context = self._context
        if context.get('default_recheck_line') == None:
            stock_move = self.env['stock.move'].sudo().search(
                [('id', '=', context.get('default_move_id'))], limit=1)
            quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [stock_move.product_id.id]),
                                                                                    ('operation_ids', 'in', [stock_move.picking_id.picking_type_id.id]),
                                                                    '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)
                                                                    ], order='create_date desc', limit=1)
            line_ids = quality_point_id.quantitative_ids
            qualitative_ids = quality_point_id.qualitative_ids
            line_list = []
            temp_line_list = []
            counter = 0
            count = 0
            res['recheck_max_number'] = stock_move and stock_move.recheck_max_number
            for line in line_ids:
                counter += 1
                line_list_vals = {
                    'sequence': counter,
                    'dimansion_id': line.dimansion_id.id,
                    'norm_qc': line.norm_qc,
                    'tolerance_from_qc': line.tolerance_from_qc,
                    'tolerance_to_qc': line.tolerance_to_qc,
                }
                line_list.append((0, 0, line_list_vals))
            for line in qualitative_ids:
                count += 1
                line_list_vals_new = {
                    'sequence': count,
                    'item_id': line.item_id.id,
                    'answer': self.qualitative_line_ids.answer.id,
                }
                temp_line_list.append((0, 0, line_list_vals_new))

            if quality_point_id:
                res.update({
                    'quantitative_line_ids': line_list,
                    'qualitative_line_ids': temp_line_list,
                    'product_id': stock_move.product_id.id,
                    'sh_quality_point_id': quality_point_id.id,
                    'sh_message': quality_point_id.sh_instruction,
                    'type': quality_point_id.type,
                    'move_id': stock_move.id,
                    'picking_id': stock_move.picking_id.id,
                    'is_result': False,
                    'is_all_pass': False,
                    'recheck_max_number': quality_point_id.number_of_test,
                    'is_recheck': False,
                    'type_of_qc': quality_point_id.type_of_qc,
                })
        else:
            pass
        return res


    def action_pass(self):
        if self.picking_id:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'pass',
                })
            if self.move_id:
                lines = self.picking_id.move_ids_without_package.filtered(
                    lambda x: x.id != self.move_id.id and x.id > self.move_id.id and x.number_of_test > 0 and x.sh_quality_point == True)
                if len(lines) > 0:
                    return {
                        'name': 'Quality Check',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sh.stock.move.global.check',
                        'context': {'default_move_id': lines[0].id},
                        'target': 'new',
                    }

    def action_fail(self):
        context = self._context
        if self.picking_id:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'fail',
                })
            if self.move_id:
                lines = self.picking_id.move_ids_without_package.filtered(
                    lambda x: x.id != self.move_id.id and x.id > self.move_id.id and x.number_of_test > 0 and x.sh_quality_point == True)
                if len(lines) > 0:
                    return {
                        'name': 'Quality Check',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sh.stock.move.global.check',
                        'context': {'default_move_id': lines[0].id},
                        'target': 'new',
                    }

    def action_confirm_quantitative(self):
        for record in self:
            record.write({'is_result': True})
            for line in record.quantitative_line_ids:
                if line.actual_value >= line.tolerance_from_qc and line.actual_value <= line.tolerance_to_qc:
                    line.status = 'pass'
                else:
                    line.status = 'fail'
            if all(line.status == 'pass' for line in record.quantitative_line_ids):
                record.write({'is_all_pass': True})
            if not record.is_recheck:
                demand = record.move_id.product_uom_qty
                sh_quality_obj = self.env['sh.quality.check'].search([('sh_picking', '=', record.picking_id.id), ('product_id', '=', record.product_id.id)])
                if record.product_id.product_tmpl_id.sample_qc > 0:
                    if record.product_id.product_tmpl_id.sample_qc != 1:
                        if record.move_id.remaining_checked_qty >= record.product_id.product_tmpl_id.sample_qc:
                            record.move_id.remaining_checked_qty -= record.product_id.product_tmpl_id.sample_qc
                            checked_qty = record.product_id.product_tmpl_id.sample_qc
                        else:
                            checked_qty = record.move_id.remaining_checked_qty
                            record.move_id.remaining_checked_qty = 0
                    elif record.move_id.remaining_checked_qty != 0:
                        checked_qty = 1
                        record.move_id.remaining_checked_qty -= 1
                    if sh_quality_obj:
                        for x in sh_quality_obj:
                            vals = []
                            vals.append(x.remaining_qty)
                            index = sorted(vals)
                            remaining_qty = index[0] - record.product_id.product_tmpl_id.sample_qc
                    else:
                        remaining_qty = demand - record.product_id.product_tmpl_id.sample_qc
                    vals = {
                        'product_id' : record.product_id.id,
                        'sh_picking' : record.picking_id.id,
                        'sh_date': date.today(),
                        'control_point_id': record.sh_quality_point_id.id,
                        'checked_qty': checked_qty,
                        'remaining_qty': remaining_qty,
                        'state': 'fail' if not record.is_all_pass else 'pass',
                        'type_of_qc': record.type_of_qc,
                        'image_128': record.image_128,
                    }
                    data = []
                    if record.type_of_qc == 'quantitative':
                        for line in record.quantitative_line_ids:
                            data.append((0 ,0, {
                                'sequence': line.sequence,
                                'dimansion_id': line.dimansion_id.id,
                                'norm_qc': line.norm_qc,
                                'tolerance_from_qc': line.tolerance_from_qc,
                                'tolerance_to_qc': line.tolerance_to_qc,
                                'actual_value': line.actual_value,
                                'text': line.text,
                                'status': line.status,
                            }))
                        vals['quantitative_line_ids'] = data
                    else:
                        for line in record.qualitative_line_ids:
                            data.append((0 ,0, {
                                'sequence': line.sequence,
                                'item_id': line.item_id.id,
                                'answer': line.answer.id,
                                'text': line.text,
                                'status': line.status,
                            }))
                        vals['qualitative_line_ids'] = data
                    quality_check = self.env['sh.quality.check'].create(vals)
                    record.quality_check_id = quality_check.id
                    if sh_quality_obj:
                        for x in sh_quality_obj:
                            x.write({'remaining_qty': remaining_qty})
            elif record.is_recheck and record.quality_check_id:
                record.quality_check_id.state = 'fail' if not record.is_all_pass else 'pass'
                if record.type_of_qc == 'quantitative':
                    for line in record.quantitative_line_ids:
                        filter_line = record.quality_check_id.quantitative_line_ids.filtered(lambda l: l.dimansion_id.id == line.dimansion_id.id)
                        filter_line.write({'actual_value': line.actual_value, 'text': line.text, 'status': line.status})
            
            self._set_state_alert()

        return{
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'sh.stock.move.global.check',
            'name': 'Quality Check',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_confirm_qualitative(self):
        for record in self:
            record.write({'is_result': True})
            for line in record.qualitative_line_ids:
                line.status = 'fail' if not line.answer.is_answer else 'pass'
            if all(line.status == 'pass' for line in record.qualitative_line_ids):
                record.write({'is_all_pass': True})
            demand = record.move_id.product_uom_qty
            sh_quality_obj = self.env['sh.quality.check'].search([('sh_picking', '=', record.picking_id.id), ('product_id', '=', record.product_id.id)])
            if not record.is_recheck:
                if record.product_id.product_tmpl_id.sample_qc > 0:
                    if record.product_id.product_tmpl_id.sample_qc != 1:
                        if record.move_id.remaining_checked_qty >= record.product_id.product_tmpl_id.sample_qc:
                            record.move_id.remaining_checked_qty -= record.product_id.product_tmpl_id.sample_qc
                            checked_qty = record.product_id.product_tmpl_id.sample_qc
                        else:
                            checked_qty = record.move_id.remaining_checked_qty
                            record.move_id.remaining_checked_qty = 0
                    elif record.move_id.remaining_checked_qty != 0:
                        checked_qty = 1
                        record.move_id.remaining_checked_qty -= 1
                    if sh_quality_obj:
                        for x in sh_quality_obj:
                            vals = []
                            vals.append(x.remaining_qty)
                            index = sorted(vals)
                            remaining_qty = index[0] - record.product_id.product_tmpl_id.sample_qc
                    else:
                        remaining_qty = demand - record.product_id.product_tmpl_id.sample_qc
                    vals = {
                        'product_id' : record.product_id.id,
                        'sh_picking' : record.picking_id.id,
                        'sh_date': date.today(),
                        'control_point_id': record.sh_quality_point_id.id,
                        'checked_qty': checked_qty,
                        'remaining_qty': remaining_qty,
                        'state': 'fail' if not record.is_all_pass else 'pass',
                        'type_of_qc': record.type_of_qc,
                        'image_128': record.image_128,
                    }
                    data = []
                    if record.type_of_qc == 'qualitative':
                        for line in record.qualitative_line_ids:
                            data.append((0 ,0, {
                                'sequence': line.sequence,
                                'item_id': line.item_id.id,
                                'answer': line.answer.id,
                                'text': line.text,
                                'status': line.status,
                            }))
                        vals['qualitative_line_ids'] = data
                    else:
                        for line in record.quantitative_line_ids:
                            data.append((0 ,0, {
                                'sequence': line.sequence,
                                'dimansion_id': line.dimansion_id.id,
                                'norm_qc': line.norm_qc,
                                'tolerance_from_qc': line.tolerance_from_qc,
                                'tolerance_to_qc': line.tolerance_to_qc,
                                'actual_value': line.actual_value,
                                'text': line.text,
                                'status': line.status,
                            }))
                        vals['quantitative_line_ids'] = data
                    quality_check = self.env['sh.quality.check'].create(vals)
                    record.quality_check_id = quality_check.id
                    if sh_quality_obj:
                        for x in sh_quality_obj:
                            x.write({'remaining_qty': remaining_qty})
            elif record.is_recheck and record.quality_check_id:
                record.quality_check_id.state = 'fail' if not record.is_all_pass else 'pass'
                if record.type_of_qc == 'qualitative':
                    for line in record.qualitative_line_ids:
                        filter_line = record.quality_check_id.qualitative_line_ids.filtered(lambda l: l.item_id.id == line.item_id.id)
                        filter_line.write({'answer': line.answer, 'text': line.text, 'status': line.status})
            
            self._set_state_alert()

        return{
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'sh.stock.move.global.check',
            'name': 'Quality Check',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_confirm_both(self):
        """function to confirm both quantitative and qualitative"""
        for record in self:
            record.write({'is_result': True})
            
            #QUANTITATIVE
            for quantitative in record.quantitative_line_ids:
                if quantitative.actual_value >= quantitative.tolerance_from_qc and quantitative.actual_value <= quantitative.tolerance_to_qc:
                    quantitative.status = 'pass'
                else:
                    quantitative.status = 'fail'
            
            #QUALITATIVE 
            for qualitative in record.qualitative_line_ids:
                qualitative.status = 'fail' if not qualitative.answer.is_answer else 'pass'
            if all(line.status == 'pass' for line in record.quantitative_line_ids) and all(line.status == 'pass' for line in record.qualitative_line_ids):
                record.write({'is_all_pass': True})
            demand = record.move_id.product_uom_qty
            
            if not record.is_recheck:   
                demand = record.move_id.product_uom_qty
                sh_quality_obj = self.env['sh.quality.check'].search([('sh_picking', '=', record.picking_id.id), ('product_id', '=', record.product_id.id)])
                if record.product_id.product_tmpl_id.sample_qc > 0:
                    if record.product_id.product_tmpl_id.sample_qc != 1:
                        if record.move_id.remaining_checked_qty >= record.product_id.product_tmpl_id.sample_qc:
                            record.move_id.remaining_checked_qty -= record.product_id.product_tmpl_id.sample_qc
                            checked_qty = record.product_id.product_tmpl_id.sample_qc
                        else:
                            checked_qty = record.move_id.remaining_checked_qty
                            record.move_id.remaining_checked_qty = 0
                    elif record.move_id.remaining_checked_qty != 0:
                        checked_qty = 1
                        record.move_id.remaining_checked_qty -= 1
                    if sh_quality_obj:
                        for x in sh_quality_obj:
                            vals = []
                            vals.append(x.remaining_qty)
                            index = sorted(vals)
                            remaining_qty = index[0] - record.product_id.product_tmpl_id.sample_qc
                    else:
                        remaining_qty = demand - record.product_id.product_tmpl_id.sample_qc
                    vals = {
                        'product_id' : record.product_id.id,
                        'sh_picking' : record.picking_id.id,
                        'sh_date': date.today(),
                        'control_point_id': record.sh_quality_point_id.id,
                        'checked_qty': checked_qty,
                        'remaining_qty': remaining_qty,
                        'state': 'fail' if not record.is_all_pass else 'pass',
                        'type_of_qc': record.type_of_qc,
                        'image_128': record.image_128,
                    }
                    data_quantitative = []
                    data_qualitative = []
                    
                    if record.type_of_qc == 'both':
                        for line in record.quantitative_line_ids:
                            data_quantitative.append((0 ,0, {
                                'sequence': line.sequence,
                                'dimansion_id': line.dimansion_id.id,
                                'norm_qc': line.norm_qc,
                                'tolerance_from_qc': line.tolerance_from_qc,
                                'tolerance_to_qc': line.tolerance_to_qc,
                                'actual_value': line.actual_value,
                                'text': line.text,
                                'status': line.status,
                            }))
                        vals['quantitative_line_ids'] = data_quantitative
                        
                    
                        for line in record.qualitative_line_ids:
                            data_qualitative.append((0 ,0, {
                                'sequence': line.sequence,
                                'item_id': line.item_id.id,
                                'answer': line.answer.id,
                                'text': line.text,
                                'status': line.status,
                            }))
                        vals['qualitative_line_ids'] = data_qualitative
                    
                    quality_check = self.env['sh.quality.check'].create(vals)
                    record.quality_check_id = quality_check.id
                    if sh_quality_obj:
                        for x in sh_quality_obj:
                            x.write({'remaining_qty': remaining_qty})
                            
            elif record.is_recheck and record.quality_check_id:
                record.quality_check_id.state = 'fail' if not record.is_all_pass else 'pass'
                if record.type_of_qc == 'both':
                    for line in record.quantitative_line_ids:
                        filter_line = record.quality_check_id.quantitative_line_ids.filtered(lambda l: l.dimansion_id.id == line.dimansion_id.id)
                        filter_line.write({'actual_value': line.actual_value, 'text': line.text, 'status': line.status})
            
            self._set_state_alert()
            
        return{
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'sh.stock.move.global.check',
            'name': 'Quality Check',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        
    def _set_state_alert(self):
        active_id = self.env.context.get('active_id')
        picking_id = self.env['stock.picking'].browse(active_id)
        alerts = self.env['sh.quality.alert'].search([('piking_id', '=', picking_id.id)])
        if alerts:
            for alert in alerts:
                alert.stage_id = 2
                

    def action_recheck_quantitative(self):
        for record in self:
            record.write({'is_result': False, 'is_all_pass': False, 'is_recheck': True})
            # record.move_id.recheck_max_number -= 1
            # record.recheck_max_number = record.move_id.recheck_max_number
            maximum_of_check = record.recheck_max_number
            maximum_of_check -= 1
            record.recheck_max_number = maximum_of_check 
        return{
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'sh.stock.move.global.check',
            'name': 'Quality Check',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_scrap_quantitative(self):
        scrap_obj = self.env['stock.scrap'].search([('quality_check_id', '=', self.quality_check_id.id)], limit=1)
        if scrap_obj:
            return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Scrap',
            'res_model': 'stock.scrap',
            'res_id': scrap_obj.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
        else:
            stock_scrap_location = self.env['stock.scrap']._get_default_scrap_location_id()
            ctx = {
                'default_product_id': self.product_id.id,
                'default_scrap_qty': self.quality_check_id.checked_qty,
                'default_product_uom_id': self.product_id.uom_id.id,
                'default_location_id': self.picking_id.location_dest_id.id,
                'default_scrap_location_id': stock_scrap_location,
                'default_quality_check_id': self.quality_check_id.id,
            }
            
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Stock Scrap',
                    'res_model': 'stock.scrap',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'context': ctx,
                    'target': 'new',
            }

    def action_repair_quantitative(self):
        repair_obj = self.env['repair.order'].search([('quality_check_id', '=', self.quality_check_id.id)], limit=1)
        if repair_obj:
            return {
            'type': 'ir.actions.act_window',
            'name': 'Repair Order',
            'res_model': 'repair.order',
            'res_id': repair_obj.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
        else:
            ctx = {
                'default_quality_check_id': self.quality_check_id.id,
                'default_product_id': self.product_id.id,
                'default_product_qty': self.quality_check_id.checked_qty,
                'default_location_id': self.picking_id.location_dest_id.id
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Repair Order',
                'res_model': 'repair.order',
                'view_type': 'form',
                'view_mode': 'form',
                'context': ctx,
                'target': 'new',
            }
        
    def action_create_itr(self):
        itr_obj = self.env['internal.transfer'].search([('quality_check_id', '=', self.quality_check_id.id)], limit=1)
        if itr_obj:
            return {
            'type': 'ir.actions.act_window',
            'name': 'Internal Transfer',
            'res_model': 'internal.transfer',
            'res_id': itr_obj.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
        else:
            warehouse_id = self.picking_id.picking_type_id.warehouse_id.id
            if self.picking_id.picking_type_code == 'incoming':
                location_id = self.picking_id.location_dest_id.id
            elif self.picking_id.picking_type_code == 'outgoing':
                location_id = self.picking_id.location_id.id
            else:
                location_id = False
            ctx = {
                'default_quality_check_id': self.quality_check_id.id,
                'default_scheduled_date': fields.Datetime.now(),
                'default_destination_warehouse_id': warehouse_id,
                'default_destination_location_id': location_id,
                'default_product_line_ids': [(0, 0, {
                    'product_id': self.product_id.id,
                    'description': self.product_id.name,
                    'uom': self.product_id.uom_id.id,
                    'qty': self.quality_check_id.checked_qty,
                    'scheduled_date': fields.Datetime.now(),
                })]
            }
            return {
                'type': 'ir.actions.act_window',
                'name': 'Internal Transfer',
                'res_model': 'internal.transfer',
                'view_type': 'form',
                'view_mode': 'form',
                'context': ctx,
                'target': 'new',
                'view_id': self.env.ref('equip3_inventory_qc.view_internal_transfer_form_inherit_qc').id,
            }
            
    def action_force_pass(self):
        if self.type_of_qc == 'qualitative':
            for line in self.qualitative_line_ids:
                self.quality_check_id.qualitative_line_ids.filtered(lambda l: l.item_id.id == line.item_id.id).write({'status': 'pass'})
                self.qualitative_line_ids.filtered(lambda l: l.item_id.id == line.item_id.id).write({'status': 'pass'})
                
        elif self.type_of_qc == 'quantitative':
            for line in self.quantitative_line_ids:
                self.quality_check_id.quantitative_line_ids.filtered(lambda l: l.dimansion_id.id == line.dimansion_id.id).write({'status': 'pass'})
                self.quantitative_line_ids.filtered(lambda l: l.dimansion_id.id == line.dimansion_id.id).write({'status': 'pass'})
                
        else:
            for line in self.qualitative_line_ids:
                self.quality_check_id.qualitative_line_ids.filtered(lambda l: l.item_id.id == line.item_id.id).write({'status': 'pass'})
                self.qualitative_line_ids.filtered(lambda l: l.item_id.id == line.item_id.id).write({'status': 'pass'})
                
            for line in self.quantitative_line_ids:
                self.quality_check_id.quantitative_line_ids.filtered(lambda l: l.dimansion_id.id == line.dimansion_id.id).write({'status': 'pass'})
                self.quantitative_line_ids.filtered(lambda l: l.dimansion_id.id == line.dimansion_id.id).write({'status': 'pass'})
                
        self.write({'is_all_pass': True})
        self.quality_check_id.write({'state': 'pass'})
        
    
    def action_next_check(self):
        picking = self.env['stock.picking'].browse(self.picking_id.id)
        qc_obj = self.env['sh.quality.check'].search([('sh_picking', '=', picking.id)])
        product_list = []
        product_list_qc = []
        for x in picking.move_ids_without_package: product_list.append(x.product_id.id)
        for a in qc_obj: product_list_qc.append(a.product_id.id)
        for record in self:
            if product_list not in product_list_qc:
                return picking.quality_point()
            else:
                return record.action_next()
   
    def action_confirm_grade(self):
        qc_obj = self.env['sh.quality.check'].search([
            ('id', '=', self.quality_check_id.id),
            ('product_id', '=', self.product_id.id),
            ('sh_picking', '=', self.picking_id.id),
            ('product_grade_id', '=', False),
            ], limit=1)
        if qc_obj:
            qc_obj.write({'product_grade_id': self.product_grade_id.id})