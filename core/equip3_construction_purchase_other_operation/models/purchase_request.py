from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def prepare_line_wiz(self, rec):
        return {
            'type' : rec.type,
            'cs_material_id' : rec.cs_material_id.id,
            'cs_labour_id' : rec.cs_labour_id.id,
            'cs_overhead_id' : rec.cs_overhead_id.id,
            'cs_equipment_id' : rec.cs_equipment_id.id,
            'bd_material_id' : rec.bd_material_id.id,
            'bd_labour_id' : rec.bd_labour_id.id,
            'bd_overhead_id' : rec.bd_overhead_id.id,
            'bd_equipment_id' : rec.bd_equipment_id.id,
            'project_scope' : rec.project_scope.id,
            'section' : rec.section.id,
            'variable_ref' : rec.variable.id,
            'group_of_product' : rec.group_of_product.id,
            'product_id' : rec.product_id.id,
            'product_description': rec.name,
            'remaning_qty': 0 if rec.remaning_qty < 0 else rec.remaning_qty,
            'pr_line_id': rec.id,
            'tender_qty': 0 if rec.remaning_qty < 0 else rec.remaning_qty,
            'uom': rec.product_uom_id.id,
            'destination_warehouse': rec.dest_loc_id.id,
            'analytics_tag_ids': [(6, 0, rec.analytic_account_group_ids.ids)],
            'schedule_date': rec.date_required,
            }

    def create_purchase_tender(self):
        data = []
        for record in self:
            sh_source = ",".join(record.line_ids.mapped('request_id.name'))
            for rec in record.line_ids:
                data.append((0, 0, self.prepare_line_wiz(rec)))
            if record.is_orders:
                context = {'default_product_line_ids': data,
                           'default_sh_source': sh_source,
                           'default_branch_id': record.branch_id.id,
                           'goods_order': 1
                           }
            else:
                context = {'default_product_line_ids': data,
                           'default_sh_source': sh_source,
                           'default_branch_id': record.branch_id.id,
                           }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Purchase Tender',
            'view_mode': 'form',
            'res_model': 'purchase.tender.create.wizard',
            'target': 'new',
            'context': context,
        }

    def button_confirm_pr(self):
        res = super(PurchaseRequest, self).button_confirm_pr()
        for rec in self:
            if rec.is_subcontracting:
                is_approved = False
                for line in rec.variable_line_ids:
                    if line.state == 'approved':
                        is_approved = True
                if not is_approved:
                    raise UserError(_("There is no approved line in this purchase request"))

    def send_data_var(self, line_id):
        return{
            'cs_subcon_id': line_id.cs_subcon_id.id,
            'bd_subcon_id': line_id.bd_subcon_id.id,
            'purchase_request_id': line_id.id,
            'project_scope': line_id.project_scope.id,
            'section': line_id.section.id,
            'variable_ref': line_id.variable_ref.id,
            'variable': line_id.variable.id,
            'quantity': line_id.quantity,
            'budget_qty': line_id.quantity,
            'uom': line_id.uom.id,
            'budget_amount': line_id.cs_subcon_id.price_unit,
            'reference_price': line_id.cs_subcon_id.price_unit,
        }

    def send_data_var_det(self, record, line):
        return{
            'project_scope': line.project_scope.id,
            'section': line.section.id,
            'variable': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product': line.product.id,
            'description': line.description,
            'quantity': line.quantity,
            'budget_quantity': line.quantity,
            'uom': line.uom.id,
            'analytic_tag_ids': record.analytic_account_group_ids.ids,
        }

    def create_purchase_agreement(self):
        data = []
        material = []
        service = []
        labour = []
        equipment = []
        overhead = []
        for record in self:
            record.purchase_req_state = 'in_progress'
            for line_id in record.variable_line_ids:
                if line_id.state != 'canceled':
                    data.append((0, 0, record.send_data_var(line_id)))
            # for line in record.material_line_ids:
            #     mat_data = record.send_data_var_det(record, line)
            #     mat_data.update({
            #         'var_material_id': line.var_material_id.id,
            #         'bd_subcon_id': line.bd_subcon_id.id or False,
            #         'cs_subcon_id': line.cs_subcon_id.id or False,
            #         })
            #     material.append((0, 0, mat_data))
            # for line in record.service_line_ids:
            #     service.append((0, 0, record.send_data_var_det(record, line)))
            # for line in record.labour_line_ids:
            #     labour.append((0, 0, record.send_data_var_det(record, line)))
            # for line in record.equipment_line_ids:
            #     equipment.append((0, 0, record.send_data_var_det(record, line)))
            # for line in record.overhead_line_ids:
            #     overhead.append((0, 0, record.send_data_var_det(record, line)))
            context = {
                'services_good': 1, 
                'default_is_services_orders' : True, 
                'default_set_single_delivery_date': True, 
                'default_set_single_delivery_destination': True, 
                'default_is_subcontracting': True, 
                'default_sh_delivery_date': record.request_date,
                'default_branch_id': record.branch_id.id, 
            }
            purchase_tender = self.env['purchase.agreement'].with_context(context).create({
                    'sh_purchase_user_id' : record.requested_by.id,
                    'is_subcontracting':True,
                    'is_services_orders':True,
                    'sh_source' : record.name,
                    'company_id' : record.company_id.id,
                    'branch_id': record.branch_id.id,
                    'variable_line_ids' : data,
                    # 'material_line_ids' : material,
                    # 'service_line_ids' : service,
                    # 'equipment_line_ids' : equipment,
                    # 'labour_line_ids' : labour,
                    # 'overhead_line_ids' : overhead,
                    'purchase_request_id' : record.id,
                    'project': record.project.id,
                    'cost_sheet': record.cost_sheet.id,
                    'project_budget': record.project_budget.id,
                    'account_tag_ids': record.analytic_account_group_ids.ids,
            })
            purchase_tender._send_line_PR()
            purchase_tender._onchange_cost_sheet(True)
            purchase_tender._get_material_line()
            for line in purchase_tender.variable_line_ids:
                line._onchange_subcon()
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchaes Tender',
                'view_mode': 'form',
                'res_model': 'purchase.agreement',
                'res_id' : purchase_tender.id,
                'target': 'current',
                'context': context,
            }

    def sh_quotation_revision(self, default=None):
        res = super(PurchaseRequest, self).sh_quotation_revision()
        for rec in self:
            purchase_request_revision = self.env['purchase.request'].search([('origin', '=', rec.name)], limit=1)
            if purchase_request_revision:
                subcons = []
                for subcon in self.variable_line_ids:
                    subcons.append((
                        0, 0, {
                            'cs_subcon_id': subcon.cs_subcon_id.id,
                            'bd_subcon_id': subcon.bd_subcon_id.id or False,
                            'project_scope': subcon.project_scope.id or False,
                            'section': subcon.section.id or False,
                            'variable': subcon.variable.id or False,
                            'quantity': subcon.quantity,
                            'uom': subcon.uom.id or False,
                            'analytic_group': subcon.analytic_group or False,
                            'rfq_variable_id': subcon.rfq_variable_id.id or False,
                            'pt_variable_id': subcon.pt_variable_id.id or False,
                        }
                    ))
                purchase_request_revision.write({
                    'variable_line_ids': subcons
                })
        return res

    # pt_variable_id = fields.Many2one('pt.variable.line', invisible=True)


class VariableLine(models.Model):
    _inherit = 'pr.variable.line'

    pt_variable_id = fields.Many2one('pt.variable.line', invisible=True)

    def cancel_variable(self):
        rec = super(VariableLine, self).cancel_variable()
        for res in self:
            if res.pt_variable_id:
                if res.pt_variable_id.state == 'draft' or res.pt_variable_id.purchase_request_id.state == 'canceled':
                    if res.bd_subcon_id:
                        res_qty_bd = res.bd_subcon_id.qty_res - res.quantity
                        res.update_res_bd(res, res_qty_bd)
                        res_qty_cs = res.cs_subcon_id.reserved_qty - res.quantity
                        res.update_res_cs(res, res_qty_cs)
                        res.write({'state' : 'canceled'})
                    else:
                        res_qty_cs = res.cs_subcon_id.reserved_qty - res.quantity
                        res.update_res_cs(res, res_qty_cs)
                        res.write({'state' : 'canceled'})
                else:
                    raise ValidationError(_("Please cancel the purchase tender first"))
            else:
                res.state = 'canceled'
        return rec


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    @api.model   
    def create_purchase_agreement(self):
        return