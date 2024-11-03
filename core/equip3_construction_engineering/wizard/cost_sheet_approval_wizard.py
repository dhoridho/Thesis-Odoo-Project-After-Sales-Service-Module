from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class CostSheetApprovalWizard(models.TransientModel):
    _inherit = 'cost.sheet.approval.wizard'

    def action_approved(self):
        res = super(CostSheetApprovalWizard, self).action_approved()
        def _create_mp(sale):
            def _mp_value(sale):
                return {
                    'name' : self.job_sheet_id.project_id.name + " - " + manuf.project_scope.name + " - " + manuf.section_name.name,
                    'project_id' : self.job_sheet_id.project_id.id,
                    'cost_sheet' : self.job_sheet_id.id,
                    'analytic_tag_ids' : self.job_sheet_id.project_id.analytic_idz,
                    'contract' : sale.id,
                }
            mp = self.env['mrp.plan'].create(_mp_value(sale))
            return mp

        def _create_mo(sale):
            def _mo_value(mp_id):
                return {
                    'project_id' : self.job_sheet_id.project_id.id,
                    'project_scope' : manuf.project_scope.id,
                    'section_name' : manuf.section_name.id,
                    'variable_ref' : manuf.variable_ref.id,
                    'final_finish_good_id' : manuf.final_finish_good_id.id,
                    'contract' : sale.id,
                    'cost_sheet' : self.job_sheet_id.id,
                    'mrp_plan_id' : mp_id.id,
                    'product_id': manuf.finish_good_id.id,
                    'product_qty': manuf.product_qty,
                    'bom_id': manuf.bom_id.id,
                    'user_id': self.env.user.id,
                    'product_uom_id': manuf.finish_good_id.uom_id.id,
                    'date_planned_start': mp_id.date_planned_start,
                    'date_planned_finished': mp_id.date_planned_finished,
                    'analytic_tag_ids': [(6, 0, mp_id.analytic_tag_ids.ids)],
                    'cs_manufacture_id': manuf.id,
                }    
            mp_name = self.job_sheet_id.project_id.name + " - " + manuf.project_scope.name + " - " + manuf.section_name.name
            mp_id = self.env['mrp.plan'].search([('name', '=', mp_name), ('contract', '=', sale.id)])
            mo = self.env['mrp.production'].create(_mo_value(mp_id))
            mo.onchange_product_id()
            mo.onchange_branch()
            mo._onchange_workorder_ids()
            mo._onchange_move_raw()
            mo._onchange_move_finished()
            mo.onchange_workorder_ids()
            mo._onchange_location_dest()
            return mo

        def _create_jo(sale, mo_id):
            def _jo_value(sale, mo_id):
                return {
                    'name' : self.job_sheet_id.project_id.name + " - " + manuf.project_scope.name + " - " + manuf.section_name.name + " - " + manuf.finish_good_id.display_name,
                    'state': 'draft',
                    'project_id' : self.job_sheet_id.project_id.id,
                    'is_engineering' : True,
                    'cost_sheet': self.job_sheet_id.id,
                    'production_id': mo_id.id,
                    'company_id': self.env.company.id,
                    'partner_id' : self.job_sheet_id.project_id.partner_id.id,
                    'sale_order' : sale.id,
                    'branch_id' : self.job_sheet_id.branch_id.id,
                    'sale_order': sale.id,
                    'project_director': self.job_sheet_id.project_id.project_director.id,
                }
            self.env['project.task'].create(_jo_value(sale, mo_id))

        def _stage_comp_val(sale):
            return {
               'name' : sale, 
            }

        scope_mp = {}
        section_jo = {}
        if self.job_sheet_id.manufacture_line:
            sale = self.env['sale.order.const'].search([('project_id', '=', self.job_sheet_id.project_id.id), ('contract_category', '=', 'main'), ('state', '=', 'sale')])
            # stage = self.env['project.completion.const'].create(sale)
            # stage.scope_as_stage()
            for manuf in self.job_sheet_id.manufacture_line:
                stage = False
                mo_id = False
                scope_name = manuf.project_scope.name + manuf.section_name.name
                sec_fg_bom = manuf.project_scope.name + manuf.section_name.name + manuf.finish_good_id.name
                # MP
                if scope_name in scope_mp:
                    pass
                else:
                    scope_mp[scope_name] = {}
                    mp = _create_mp(sale)
                # jO
                if sec_fg_bom in section_jo:
                    pass
                else:
                    section_jo[sec_fg_bom] = {}
                    # stage = _create_stage(scope_name)
                    mo_id = _create_mo(sale)
                    _create_jo(sale, mo_id)
                if mp:
                    mp.generate_mrp_order_ids()
        return res
