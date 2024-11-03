# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sh_quality_check_ids = fields.Many2many(
        'sh.quality.check', string="Quality Checks", compute='_get_quality_check_ids')
    sh_quality_alert_ids = fields.Many2many(
        'sh.quality.alert', string="Quality Alert", compute='_get_quality_alert_ids')
    qc_count = fields.Integer('Quality Checks Count', compute='_get_qc_count')
    qc_alert_count = fields.Integer(
        'Quality Alerts', compute='_get_qc_alert_count')
    need_qc = fields.Boolean(
        "Need QC", compute='_check_need_qc', search='search_need_qc')
    qc_fail = fields.Boolean(
        "QC Fail", compute='_check_need_qc', search='search_fail_qc')
    qc_pass = fields.Boolean(
        "QC Pass", compute='_check_need_qc', search='search_pass_qc')
    full_pass = fields.Boolean(
        "Full Pass", compute='_check_need_qc', search='search_full_pass_qc')
    is_mandatory = fields.Boolean(
        "QC Mandatory", compute='_check_qc_mandatory', search='search_mandatory_qc')
    attachment_ids = fields.Many2many(
        'ir.attachment', string="QC Pictures", copy=False)

    def search_need_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.need_qc and not rec_id.qc_fail and not rec_id.qc_pass and not rec_id.full_pass:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def search_fail_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.qc_fail:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def search_pass_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.qc_pass and rec_id.need_qc:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def search_mandatory_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.is_mandatory:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def search_full_pass_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.full_pass and rec_id.need_qc:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def _check_qc_mandatory(self):
        if self:
            for rec in self:
                rec.is_mandatory = False
                if rec.move_ids_without_package:
                    for move in rec.move_ids_without_package:
                        quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [move.product_id.id]),
                                                                                  ('operation_ids', 'in', [move.picking_id.picking_type_id.id]),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)
                                                                  ], limit=1, order='create_date desc')

                        quality_point_id_not_in_team = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [move.product_id.id]),
                                                                                  ('operation_ids', 'in', [move.picking_id.picking_type_id.id]),
                                                                                  ('is_mandatory', '=', True),
                                                                  '|', ('team.user_ids.id', 'not in', [self.env.uid]), ('team', '!=', False)
                                                                  ], limit=1, order='create_date desc')
                        if quality_point_id.is_mandatory or quality_point_id_not_in_team.is_mandatory:
                            rec.is_mandatory = True

    def _check_need_qc(self):
        if self:
            for rec in self:
                rec.qc_pass = False
                rec.qc_fail = False
                rec.need_qc = False
                rec.full_pass = False
                
                
                if rec.move_ids_without_package:
                    for move in rec.move_ids_without_package:
                        
                        quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [move.product_id.id]),
                                                                                  ('operation_ids', 'in', [move.picking_id.picking_type_id.id]),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)
                                                                  ], limit=1, order='create_date desc')

                        quality_point_id_not_in_team = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [move.product_id.id]),
                                                                                  ('operation_ids', 'in', [move.picking_id.picking_type_id.id]),
                                                                                  ('is_mandatory', '=', True),
                                                                  '|', ('team.user_ids.id', 'not in', [self.env.uid]), ('team', '!=', False)
                                                                  ], limit=1, order='create_date desc')
                                                      
                        if quality_point_id or quality_point_id_not_in_team:
                            rec.need_qc = True
                        if move.sh_last_qc_state == 'fail':
                            rec.qc_fail = True
                            rec.qc_pass = False
                        if move.sh_last_qc_state == 'pass' and rec.qc_fail == False:
                            rec.qc_pass = True
                            
                if len(rec.sh_quality_check_ids.filtered(lambda x: x.sh_picking.id == rec.id and x.state == 'pass')) > 0:
                    if rec.move_ids_without_package:
                        quality_point_count = 0
                        full_pass = True
                        for move in rec.move_ids_without_package:
                            quality_point_id = self.env['sh.qc.point'].sudo().search([
                                ('product_ids', 'in', [move.product_id.id]),('operation_ids', 'in', [move.picking_id.picking_type_id.id]),
                                '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)], limit=1, order='create_date desc')

                            if quality_point_id:
                                quality_point_count += 1
                                
                            check_id = self.env['sh.quality.check'].sudo().search([('product_id','=',move.product_id.id),
                                                                                   ('sh_picking','=',rec.id)], order='id desc',limit=1)
                            
                            if check_id.state != 'pass':
                                full_pass = False
                                
                        if full_pass:
                            rec.full_pass = True
                            rec.qc_fail = False
                            rec.qc_pass = False
                if rec.need_qc == False:
                    rec.qc_pass = True
                    

    def _get_qc_count(self):
        if self:
            for rec in self:
                rec.qc_count = 0
                qc = self.env['sh.quality.check'].search(
                    [('sh_picking', '=', rec.id)])
                rec.qc_count = len(qc.ids)

    def _get_qc_alert_count(self):
        if self:
            for rec in self:
                rec.qc_alert_count = 0
                qlarts = self.env['sh.quality.alert'].search(
                    [('piking_id', '=', rec.id)])
                rec.qc_alert_count = len(qlarts.ids)

    def _get_quality_check_ids(self):
        if self:
            for rec in self:
                rec.sh_quality_check_ids = False
                quality_check_ids = self.env['sh.quality.check'].search(
                    [('sh_picking', '=', rec.id)])
                if quality_check_ids:
                    rec.sh_quality_check_ids = [(6, 0, quality_check_ids.ids)]

    def _get_quality_alert_ids(self):
        if self:
            for rec in self:
                rec.sh_quality_alert_ids = False
                quality_alert_ids = self.env['sh.quality.alert'].search(
                    [('piking_id', '=', rec.id)])
                if quality_alert_ids:
                    rec.sh_quality_alert_ids = [(6, 0, quality_alert_ids.ids)]

    def quality_point(self):
        if self and self.move_ids_without_package:
#             line = self.move_ids_without_package
            need_qc = False
            line_id = False
            for line in self.move_ids_without_package:
                quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [line.product_id.id]),
                                                                                  ('operation_ids', 'in', [line.picking_id.picking_type_id.id]),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)
                                                                  ], limit=1, order='create_date desc')
                
                if quality_point_id:
                    line.write({'sh_quality_point_id': quality_point_id.id, 'sh_quality_point': True})
                    if not need_qc and line.number_of_test > 0:
                        line_id = line.id
                        need_qc = True

            if need_qc:
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.stock.move.global.check',
                    'context': {'default_move_id': line_id},
                    'target': 'new',
                }

    def action_quality_alert(self):
        line_ids = []
        if self.move_ids_without_package:
            for line in self.move_ids_without_package:
                vals = {
                    'product_id': line.product_id.id,
                    'partner_id': self.partner_id.id,
                }
                line_ids.append((0, 0, vals))
        return {
            'name': 'Quality Alert',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.qc.alert',
            'context': {'default_alert_ids': line_ids},
            'target': 'new',
        }

    def open_quality_check(self):
        po = self.env['sh.quality.check'].search(
            [('sh_picking', '=', self.id)])
        action = self.env.ref('sh_inventory_mrp_qc.quality_check_action').read()[0]
        action['context'] = {
            'domain': [('id', 'in', po.ids)]

        }
        action['domain'] = [('id', 'in', po.ids)]
        return action

    def open_quality_alert(self):
        alert_ids = self.env['sh.quality.alert'].search(
            [('piking_id', '=', self.id)])
        action = self.env.ref('sh_inventory_mrp_qc.quality_alert_action').read()[0]
        action['context'] = {
            'domain': [('id', 'in', alert_ids.ids)]
        }
        action['domain'] = [('id', 'in', alert_ids.ids)]
        return action


class StockMove(models.Model):
    _inherit = 'stock.move'

    sh_quality_point = fields.Boolean('Quality Point')
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    sh_last_qc_date = fields.Datetime(
        'Last Quality Check Date', compute='_get_last_check_result')
    sh_last_qc_state = fields.Char(
        'Last Quality Check Status', compute='_get_last_check_result')
    number_of_test = fields.Integer(
        "Maximum number of tests allowed.", compute='_get_last_check_result')
    
    @api.model
    def create(self, vals):
        if vals.get('picking_type_id') and vals.get('product_id'):
            quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in',[vals.get('product_id')]),
                ('operation_ids', 'in', [vals.get('picking_type_id')]),'|', 
                ('team.user_ids.id', 'in', [self.env.context.get('uid')]), 
                ('team', '=', False)], limit=1, order='create_date desc')

            quality_point_id_not_in_team = self.env['sh.qc.point'].sudo().search([('product_ids', 'in',[vals.get('product_id')]),
                    ('is_mandatory', '=', True),
                    ('operation_ids', 'in', [vals.get('picking_type_id')]),'|', 
                    ('team.user_ids.id', 'in', [self.env.context.get('uid')]), 
                    ('team', '!=', False)], limit=1, order='create_date desc')

            if quality_point_id or quality_point_id_not_in_team:
                vals.update({'sh_quality_point':True, 'sh_quality_point_id':quality_point_id.id})
        return super(StockMove, self).create(vals)

    def _get_last_check_result(self):
        if self:
            for rec in self:
                rec.sh_last_qc_date = False
                rec.sh_last_qc_state = ''
                check_count = rec.picking_id.sh_quality_check_ids.filtered(
                    lambda x: x.product_id.id == rec.product_id.id)
                quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [rec.product_id.id]),
                                                                                  ('operation_ids', 'in', [rec.picking_id.picking_type_id.id]),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)
                                                                  ], limit=1, order='create_date desc')
                        
                number_of_test = 100
                if quality_point_id :
                    if quality_point_id.number_of_test > 0:
                        number_of_test = quality_point_id.number_of_test
                    
                rec.number_of_test = number_of_test - len(check_count)
                last_quality_check = self.env['sh.quality.check'].search(
                    [('product_id', '=', rec.product_id.id), ('sh_picking', '=', rec.picking_id.id)], limit=1, order='create_date desc')
                if last_quality_check:
                    rec.sh_last_qc_date = last_quality_check.create_date
                    rec.sh_last_qc_state = str(last_quality_check.state)
                            

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(StockMove, self).onchange_product_id()
        quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [self.product_id.id]), ('operation_ids', 'in', [self.picking_id.picking_type_id.id]),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)], limit=1, order='create_date desc')
        quality_point_id_not_in_team = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [self.product_id.id]), ('operation_ids', 'in', [self.picking_id.picking_type_id.id]),('is_mandatory','=', True),
                                                                  '|', ('team.user_ids.id', 'not in', [self.env.uid]), ('team', '!=', False)], limit=1, order='create_date desc')
        if quality_point_id or quality_point_id_not_in_team:
            self.sh_quality_point = True
            self.sh_quality_point_id = quality_point_id.id
            self.number_of_test = self.sh_quality_point_id.number_of_test
        return res

    def quality_point_line(self):
        quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [self.product_id.id]), ('operation_ids', 'in', [self.picking_id.picking_type_id.id]),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)], limit=1, order='create_date desc')
        
        if quality_point_id:
            self.write({'sh_quality_point_id': quality_point_id.id, 'sh_quality_point': True})
            
        if self.sh_quality_point_id.type == 'type2':
            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.stock.move.qc.measurement',
                'context': {'default_picking_id': self.picking_id.id},
                'target': 'new',
            }
        elif self.sh_quality_point_id.type == 'type1':
            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.stock.move.pass.fail',
                'context': {'default_picking_id': self.picking_id.id},
                'target': 'new',
            }
        elif self.sh_quality_point_id.type == 'type3':
            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.stock.move.pics',
                'context': {'default_picking_id': self.picking_id.id},
                'target': 'new',
            }
        elif self.sh_quality_point_id.type == 'type4':
            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.stock.move.text',
                'context': {'default_picking_id': self.picking_id.id},
                'target': 'new',
            }

    def quality_alert(self):
        return {
            'name': 'Quality Alerts',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.quality.alert',
            'context': {'default_stage_id': self.env.ref('sh_inventory_mrp_qc.alert_stage_0').id, 'default_product_id': self.product_id.id, 'default_piking_id': self.picking_id.id, 'default_partner_id': self.picking_id.partner_id.id},
            'target': 'current',
        }
