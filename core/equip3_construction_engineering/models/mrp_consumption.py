# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round


class MrpConsumption(models.Model):
    _inherit = 'mrp.consumption'

    project_id = fields.Many2one('project.project', string='Project', related='manufacturing_order_id.project_id')
    contract = fields.Many2one('sale.order.const', string="Contract", related='manufacturing_order_id.contract')
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet', force_save="1", related='manufacturing_order_id.cost_sheet')
    project_budget = fields.Many2one('project.budget', string='Periodical Budget', domain="[('project_id','=', project_id)]", force_save="1")
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', related='project_id.budgeting_method', store = True)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', related='manufacturing_order_id.project_scope')
    section_name = fields.Many2one('section.line', string='Section', related='manufacturing_order_id.section_name')
    variable_ref = fields.Many2one('variable.template', string='Variable', related='manufacturing_order_id.variable_ref')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods', related='manufacturing_order_id.final_finish_good_id')
    cs_manufacture_id = fields.Many2one('cost.manufacture.line', 'CS Manufacture ID', related='manufacturing_order_id.cs_manufacture_id')
    bd_manufacture_id = fields.Many2one('budget.manufacture.line', 'BD Manufacture ID', related='manufacturing_order_id.bd_manufacture_id')
    job_order = fields.Many2one('project.task', string='Job Order')
    progress_start = fields.Datetime(string='Progress Start')

    def _update_stock_valuation_layers(self):
        res = super(MrpConsumption, self)._update_stock_valuation_layers()
        for rec in self:
            for line in self.move_raw_ids:
                if rec.project_budget:
                    pass
                else:
                    cs_line = rec.env['material.material'].search([('job_sheet_id', '=', rec.cost_sheet.id), 
                                                                    ('project_scope', '=', rec.project_scope.id),
                                                                    ('section_name', '=', rec.section_name.id), 
                                                                    ('variable_ref', '=', rec.variable_ref.id),
                                                                    ('final_finish_good_id', '=', rec.final_finish_good_id.id),
                                                                    ('finish_good_id', '=', rec.product_id.id),
                                                                    ('product_id', '=', line.product_id.id)])
                    cs_line.update({
                        'actual_used_qty': cs_line.actual_used_qty + line.quantity_done,
                        'actual_used_amt': cs_line.actual_used_amt + line.cost,
                    })
        return res

    def _prepare_vals_self_task(self, rec, latest, progress, finished, rejected):
        summary = (("Finished = '{}' Unit(s).\nRejected = '{}' Unit(s)".format(finished, rejected)))
        return {
            'project_id': rec.project_id.id,
            'sale_order': rec.sale_order.id,
            'job_estimate': rec.job_estimate.id,
            'purchase_subcon': rec.purchase_subcon.id,
            'completion_ref': rec.completion_ref.id,
            'stage_new': rec.stage_new.id,
            'stage_computed_new': [(6, 0, [v.id for v in rec.stage_computed_new])],
            'work_order': rec.id,
            'name': rec.name,
            'subtask': False,
            'production_id': self.manufacturing_order_id.id,
            'workorder_id': self.workorder_id.id,
            'record_id': self.id,
            'progress_start_date_new': self.progress_start,
            'progress_end_date_new': datetime.now(),
            'latest_completion': latest,
            'progress': progress,
            'approved_progress': progress,
            'progress_summary': summary,
            'create_by': self.create_uid.id,
            'date_create': datetime.now(),
            'is_progress_history_approval_matrix': rec.is_progress_history_approval_matrix,
            'attachment_ids': False,
            'progress_wiz': False,
            'request_status': 'approved'
        }
    
    def button_confirm(self):
        res = super(MrpConsumption, self).button_confirm()
        job_order = self.job_order
        workorder = self.workorder_id
        production = self.manufacturing_order_id
        done_moves = production.move_finished_ids.filtered(lambda x: x.state != 'cancel' and x.product_id.id == production.product_id.id)
        qty_produced = sum(done_moves.mapped('quantity_done'))
        if self.rejected_qty:
                if self.bd_manufacture_id:
                    self.bd_manufacture_id.update({
                        'rejected_qty': self.bd_manufacture_id.rejected_qty + self.rejected_qty
                    })
                else:
                    self.cs_manufacture_id.update({
                        'rejected_qty': self.cs_manufacture_id.rejected_qty + self.rejected_qty
                    })
        if qty_produced:
            if self.finished_qty:
                if self.bd_manufacture_id:
                    self.bd_manufacture_id.update({
                        'manuf_create_qty': self.bd_manufacture_id.manuf_create_qty + qty_produced
                    })
                else:
                    self.cs_manufacture_id.update({
                        'manuf_create_qty': self.cs_manufacture_id.manuf_create_qty + qty_produced
                    })
        
        # Create Progress History
        to_consume = production.product_qty
        produced = production.qty_produced
        finished = self.finished_qty
        rejected = self.rejected_qty
        weightage = workorder.weightage
        progress = (finished / to_consume) * (weightage / 100) * 100
        if job_order:
            progress_line = self.env['progress.history'].search([('work_order', '=', job_order.id),('production_id', '=', production.id)], limit=1, order='create_date desc')
            if progress_line:
                latest = progress_line.latest_completion + progress_line.progress
            else:
                latest = 0
            for rec in job_order:
                self.env['progress.history'].sudo().create(self._prepare_vals_self_task(rec, latest, progress, finished, rejected))
            if finished + produced >= to_consume:
                job_order.write({'actual_end_date': datetime.now(),
                                 'state': 'complete'})
        return res
            