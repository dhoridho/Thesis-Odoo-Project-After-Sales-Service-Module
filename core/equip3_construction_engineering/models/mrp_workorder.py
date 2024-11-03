from odoo import fields, models, api, _
from odoo.tools import float_round
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    project_id = fields.Many2one('project.project', string='Project', related='production_id.project_id')
    contract = fields.Many2one('sale.order.const', string="Contract", related='production_id.contract' )
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', related='production_id.project_scope')
    section_name = fields.Many2one('section.line', string='Section', related='production_id.section_name')
    variable_ref = fields.Many2one('variable.template', string='Variable', related='production_id.variable_ref')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods', related='production_id.final_finish_good_id')
    cs_manufacture_id = fields.Many2one('cost.manufacture.line', 'CS Manufacture ID', related='production_id.cs_manufacture_id')
    bd_manufacture_id = fields.Many2one('budget.manufacture.line', 'BD Manufacture ID', related='production_id.bd_manufacture_id')
    weightage = fields.Float(string="Weightage", default=0.00)
    job_order = fields.Many2one(related='production_id.job_order', string='Job Order')
    progress_start = fields.Datetime(string='Progress Start')

    def _prepare_consumption_vals(self):
        self.ensure_one()

        approval_matrix_id = False
        if self.env.company.production_record_conf:
            approval_matrix_id = self.env['mrp.consumption']._default_approval_matrix(company=self.company_id, branch=self.branch)
            if not approval_matrix_id:
                raise ValidationError(_('Please set approval matrix for Production Record first!'))
        
        bom_data = self.production_id._read_bom_data(origin=True)[self.production_id.bom_id.id]
        bom_product_qty = bom_data['product_qty']
        bom_product_uom = self.env['uom.uom'].browse(bom_data['product_uom_id']['id'])

        move_raw_values = self._get_mpr_move_raw_vals(bom_product_qty, bom_product_uom, bom_data['bom_line_ids'])
        byproduct_values = self._get_mpr_byproduct_vals(bom_product_qty, bom_product_uom, bom_data['byproduct_ids'])
        move_finished_values = self._get_mpr_move_finished_vals()

        return {
            'manufacturing_plan': self.mrp_plan_id.id,
            'create_date': fields.Datetime.now(),
            'create_uid': self.env.uid,
            'manufacturing_order_id': self.production_id.id,
            'workorder_id': self.id,
            'product_id': self.product_id.id,
            'finished_qty': self.qty_remaining,
            'rejected_qty': 0.0,
            'date_finished': fields.Datetime.now(),
            'is_last_workorder': self._is_last_workorder(),
            'move_raw_ids': move_raw_values,
            'move_finished_ids': move_finished_values,
            'byproduct_ids': byproduct_values,
            'product_uom_id': self.product_uom_id.id,
            'company_id': self.company_id.id,
            'branch_id': self.branch.id,
            'approval_matrix_id': approval_matrix_id,
            'is_locked': self.env.user.has_group('mrp.group_locked_by_default'),
            'is_dedicated': self.env.company.dedicated_material_consumption,
            'project_id': self.project_id.id,
            'contract': self.contract.id,
            'job_order': self.job_order.id,
            'progress_start': self.progress_start,
        }

    def button_start(self):
        res = super(MrpWorkorder, self).button_start()
        weightage_order = 0
        for mo in self:
            if mo.job_order:
                m_order = mo.env['mrp.workorder'].search([('production_id', '=', mo.production_id.id)])
                m_order_null = mo.env['mrp.workorder'].search([('production_id', '=', mo.production_id.id), ('weightage', '=', 0), ('id', '!=', mo.id)])
                if self.weightage < 1:
                    raise ValidationError(_('The weightage for this operation must be more than 0%.'))
                
                for null in m_order_null:
                    if null:
                        raise ValidationError(_("It looks like there are still work orders with 0% weightage. Please allocate weightage to all work orders in this production order '{}'.".format(mo.production_id.name)))
                
                for weig in m_order:
                    weightage_order += weig.weightage
                
                if weightage_order > 100:
                    raise ValidationError(_("Total weightage for all operations on this Production Order '{}' is more than 100%. Please, re-set the weightage of this operation.".format(mo.production_id.name)))
                
                if weightage_order > 0 and weightage_order < 100:
                    rest = 100 - weightage_order
                    raise ValidationError(_("Total weightage for all operations on this Production Order '{}' is less than 100% (total weightage = '{}%'). Please allocate '{}%' of weightage to all work orders in this production order.".format(mo.production_id.name, weightage_order, rest)))

                for job in mo.job_order:
                    if not job.stage_new and job.work_weightage < 1: 
                        raise ValidationError(_("Please fill the stage and job weightage of job order '{}' first.".format(mo.job_order.name)))
                    if not job.stage_new: 
                        raise ValidationError(_("Please fill the stage of job order '{}' first.".format(mo.job_order.name)))
                    if job.work_weightage < 1: 
                        raise ValidationError(_("Please fill job weightage of job order '{}' first.".format(mo.job_order.name)))

                
                mo_production = mo.env['mrp.production'].search([('id', '=', mo.production_id.id)],limit=1)
                for time in mo_production:
                    if time.duration == 0:
                        mo.job_order.write({'actual_start_date': datetime.now(),
                                            'state': 'inprogress'})
                
                if mo.state == 'ready' or mo.state == 'progress':
                    mo.write({'progress_start': datetime.now()})

        return res            
    
class MRPQualityInherit(models.Model):
    _inherit = 'sh.mrp.quality.alert'

    weightage = fields.Float(string="Weightage", default=0.00)

