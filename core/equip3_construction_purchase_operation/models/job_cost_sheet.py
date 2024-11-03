from queue import Empty
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import ValidationError, UserError


class JobCostSheet(models.Model):
    _inherit = 'job.cost.sheet'
    _rec_name = 'number'
    _order = 'id DESC' 
    _check_company_auto = True
 
    total_material_request = fields.Integer(string="Material Request",compute='_comute_material_request')
    total_purchase_agreement = fields.Integer(string="Purchase Agreement",compute='_comute_purchase_agreement')
    hide_subcon_buton = fields.Boolean(string="Hide Subcon Button", compute='_comute_subcon')

    def _comute_subcon(self):
        for job in self:
            if self.budgeting_method == 'product_budget':
                if job.material_subcon_ids:
                    job.hide_subcon_buton = False
                else:
                    job.hide_subcon_buton = True
            else:
                job.hide_subcon_buton = False
        
    def create_material_request(self):
        if  self.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        
        if not self.warehouse_id:
            raise ValidationError(_("There is no Warehouse selected for this project"))
        
        context = {'default_cost_sheet': self.id,
                   'default_destination_warehouse': self.warehouse_id.id,
                   'default_budgeting_period': self.budgeting_period,
                   'default_analytic_group': [(6, 0, [v.id for v in self.account_tag_ids])],
                   }
        return {
                'type': 'ir.actions.act_window',
                'name': 'Create Request',
                'res_model': 'material.request.wiz',
                'view_type': 'form',
                'view_mode': 'form',
                'context': context,
                'target': 'new'
            }
    
    def _comute_material_request(self):
        for rec in self:
            # material_request_count = self.env['material.request'].search_count([('job_cost_sheet', '=', rec.id)])
            # convert above code to query
            rec.env.cr.execute("""
                SELECT COUNT(*) FROM material_request WHERE job_cost_sheet = %s
            """, (rec.id,))
            material_request_count = rec.env.cr.fetchone()[0]
            rec.total_material_request = material_request_count

    def _comute_purchase_agreement(self):
        for rec in self:
            # purchase_agreement_count = self.env['purchase.request'].search_count([('cost_sheet','=',rec.id), ('is_subcontracting','=',True)])
            # convert above code to query
            rec.env.cr.execute("""
                SELECT COUNT(*) FROM purchase_request WHERE cost_sheet = %s AND is_subcontracting = True
            """, (rec.id,))
            purchase_agreement_count = rec.env.cr.fetchone()[0]
            rec.total_purchase_agreement = purchase_agreement_count
            
    
    def action_material_request(self):
        return {
            'name': ("Material Request"),
            'view_mode': 'tree,form',
            'res_model': 'material.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('job_cost_sheet','=',self.id)],
        }

    def action_purchase_agreement(self):
        return {
            'name': ("Purchase Agreement"),
            'view_mode': 'tree,form',
            'res_model': 'purchase.request',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('cost_sheet','=',self.id), ('is_subcontracting','=',True)],
        }


class MaterialGopMaterialInherit(models.Model):
    _inherit = 'material.gop.material'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'cs_material_gop_id', string='Purchase Material')


class MaterialGopLabourInherit(models.Model):
    _inherit = 'material.gop.labour'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'cs_labour_gop_id', string='Purchase Material')


class MaterialGopOverheadInherit(models.Model):
    _inherit = 'material.gop.overhead'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'cs_overhead_gop_id', string='Purchase Material')


class MaterialGopEquipmentInherit(models.Model):
    _inherit = 'material.gop.equipment'

    purchase_order_line_ids = fields.One2many('purchase.order.line', 'cs_equipment_gop_id', string='Purchase Material')

    
