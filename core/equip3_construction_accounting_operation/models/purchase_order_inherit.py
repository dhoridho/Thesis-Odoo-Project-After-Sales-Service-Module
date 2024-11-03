from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class RfqVariableLineInherit(models.Model):
    _inherit =  'rfq.variable.line'

    billed_claim_perc = fields.Float(string="Billed Claim (%)")
    progressive_claim_perc = fields.Float(string="Progressive Claim (%)")


class PurchaseOrderInherit(models.Model):
    _inherit =  'purchase.order'

    claim_id = fields.Many2one('progressive.claim', string="Progressive Claim", domain="[('project_id', '=', project),('vendor', '=', partner_id),('progressive_bill', '=', True)]", ondelete='restrict')
    count_claim = fields.Integer(string="Claim", compute="_compute_count_claim")
    responsible = fields.Selection([('contractor', 'Contractor'), ('vendor', 'Vendor')], string='Responsible')
    reason = fields.Text(string='Reason')
    is_renewed = fields.Boolean(string='Is renewed')
    new_contract = fields.Many2one('purchase.order', string="New Contract")
    
    # def create_renew_contract(self):
    #     if self.is_subcontracting == True:
    #         if self.sub_contracting == 'addendum' and self.main_po_reference == 'cancel':
    #             raise ValidationError(_("Cannot create a new contract variation order for this vendor because the main contract has been cancelled"))
    #         else:
    #             renewed_contract = self.copy()
    #             renewed_contract.write({
    #                 'state': 'draft',
    #             })

    #             milestone_values = []
    #             i = 0

    #             # Copy milestone terms, append on first loop, add on second loop in order to make += works
    #             # Needed due to validation error on milestone terms
    #             if self.is_set_custom_claim:
    #                 if len(self.milestone_term_ids) > 0:
    #                     for terms in self.milestone_term_ids:
    #                         if i == 0:
    #                             milestone_values.append(terms.copy())
    #                         else:
    #                             milestone_values[0] += terms.copy()
    #                         i += 1

    #                     renewed_contract.milestone_term_ids = milestone_values[0]

    #             for variable in self.variable_line_ids:
    #                 renewed_contract.variable_line_ids += variable.copy()

    #             for material in self.material_line_ids:
    #                 renewed_contract.material_line_ids += material.copy()
                
    #             for service in self.service_line_ids:
    #                 renewed_contract.service_line_ids += service.copy()
                
    #             for equipment in self.equipment_line_ids:
    #                 renewed_contract.equipment_line_ids += equipment.copy()
                
    #             for labour in self.labour_line_ids:
    #                 renewed_contract.labour_line_ids += labour.copy()
                
    #             for overhead in self.overhead_line_ids:
    #                 renewed_contract.overhead_line_ids += overhead.copy()

    #             for order in self.order_history_line:
    #                 renewed_contract.order_history_line += order.copy()
                
    #             self.write({
    #                 'is_renewed': True,
    #                 'new_contract': renewed_contract.id,
    #             })

    #             return {
    #                 'name': _(renewed_contract.name),
    #                 'type': 'ir.actions.act_window',
    #                 'view_type': 'form',
    #                 'view_mode': 'form',
    #                 'res_model': 'purchase.order',
    #                 'res_id': renewed_contract.id,
    #                 'target': 'current',
    #             }
        
    
    def progressive_perc(self,claim_perc):
        for res in self:
            for variable in res.variable_line_ids:
                variable.write({'progressive_claim_perc': claim_perc})
            res._update_subcon_budget()

    def _update_subcon_budget(self):
        for rec in self:
            for line in rec.variable_line_ids:
                cal_qty = 0.00
                cal_amt = 0.00
                # ---- convert from perc
                cal_qty = line.progressive_claim_perc * line.quantity / 100
                cal_amt = line.progressive_claim_perc * line.sub_total / 100
                # ---- for actual used cs
                cs_act_qty = cal_qty
                cs_act_amt = cal_amt
                cs_pur_qty = cal_qty
                cs_pur_amt = cal_amt
                
                # --- substract reserved cs
                cs_res_qty = line.cs_subcon_id.reserved_qty - cal_qty
                cs_res_amt = line.cs_subcon_id.reserved_amt - cal_amt
                
                if rec.project_budget:
                    # ---- for actual used bd
                    bd_act_qty = cal_qty
                    bd_act_amt = cal_amt
                    bd_pur_qty = cal_qty
                    bd_pur_amt = cal_amt
                    # --- substract reserved bd
                    bd_res_qty = line.bd_subcon_id.qty_res - cal_qty
                    bd_res_amt = line.bd_subcon_id.amt_res - cal_amt
                    for sub in rec.project_budget:
                        sub.budget_subcon_ids = [(1, line.bd_subcon_id.id, {
                                        'qty_used': bd_act_qty,
                                        'amt_used': bd_act_amt,
                                        'qty_res': bd_res_qty,
                                        'amt_res': bd_res_amt,
                                        'purchased_qty': bd_pur_qty,
                                        'purchased_amt': bd_pur_amt,
                                    })]
                    for cs in rec.cost_sheet:
                        for cs in self.cost_sheet:
                                cs.material_subcon_ids = [(1, line.cs_subcon_id.id, {
                                        'actual_used_qty': cs_act_qty,
                                        'actual_used_amt': cs_act_amt,
                                        'reserved_qty': cs_res_qty,
                                        'reserved_amt': cs_res_amt,
                                        'purchased_qty': cs_pur_qty,
                                        'purchased_amt': cs_pur_amt,
                                    })]
                else:
                    for cs in rec.cost_sheet:
                        for cs in self.cost_sheet:
                                cs.material_subcon_ids = [(1, line.cs_subcon_id.id, {
                                        'actual_used_qty': cs_act_qty,
                                        'actual_used_amt': cs_act_amt,
                                        'reserved_qty': cs_res_qty,
                                        'reserved_amt': cs_res_amt,
                                        'purchased_qty': cs_pur_qty,
                                        'purchased_amt': cs_pur_amt,
                                    })]
                        
    def _compute_count_claim(self):
        for res in self:
            claim = 0.0
            if res.addendum_payment_method == 'split_payment':
                claim = self.env['progressive.claim'].search_count([('progressive_bill', '=', True), ('project_id', '=', res.project.id), ('contract_parent_po', '=', res.id)])
                res.count_claim = claim
            elif res.addendum_payment_method == 'join_payment':
                claim = self.env['progressive.claim'].search_count([('progressive_bill', '=', True), ('project_id', '=', res.project.id), ('contract_parent_po', '=', res.contract_parent_po.id)])
                res.count_claim = claim
            else:
                res.count_claim = claim
    
    def action_progressive_claim(self):
        if self.addendum_payment_method == 'split_payment': 
            claim2 = self.env['progressive.claim'].search([('progressive_bill', '=', True), ('project_id', '=', self.project.id), ('contract_parent_po', '=', self.id)], limit=1)
        elif self.addendum_payment_method == 'join_payment': 
            claim2 = self.env['progressive.claim'].search([('progressive_bill', '=', True), ('project_id', '=', self.project.id), ('contract_parent_po', '=', self.contract_parent_po.id)], limit=1)
        action = claim2.get_formview_action()
        return action

    def create_progressive_claim(self):
        contract = []
        for sub in self:
            contract.append(
                (0, 0, {'purchase_order_ref':  self.id,
                        'sub_contracting':  sub.sub_contracting,
                        'contract_amount':  sub.discounted_total,
                        }
                ))    
        if self.sub_contracting == 'addendum':
            context = {'default_progressive_bill': True,
                    'default_project_id': self.project.id,
                    'default_contract_parent_po': self.contract_parent_po.id,
                    }
        else:
            context = {'default_progressive_bill': True,
                    'default_project_id': self.project.id,
                    'default_contract_parent_po': self.id,
                    }
        
        context['default_is_set_custom_claim'] = self.is_set_custom_claim

        return {
            "name": "Progressive Claim",
            "type": "ir.actions.act_window",
            "res_model": "progressive.claim",
            "context": context,
            "view_mode": 'form',
            "target": "current",
        }

    def button_confirm(self):
        if self.is_subcontracting is True:
            if self.use_dp is True and self.down_payment == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.downpayment.purchase',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    }
            elif self.use_retention is True and self.retention_1 == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Confirmation',
                    'res_model': 'confirm.retention.purchase',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    }
            if self.retention_1 > 0 and self.retention_term_1 == False:
                raise ValidationError(_("You haven't set Retention 1 Date for this contract"))
            elif self.retention_2 > 0 and self.retention_term_2 == False:
                raise ValidationError(_("You haven't set Retention 2 Date for this contract"))
            else:

                for record in self:
                    if record.budgeting_method in (
                            'product_budget', 'gop_budget') and not record.is_continue_over_budget:
                        for rec in record.variable_line_ids:
                            record.validate_amount(rec)

                            if record.project_budget:
                                if rec.total > rec.budget_amount_total:
                                    if record.cost_sheet.is_over_budget_ratio:
                                        over_budget_limit = (rec.budget_amount_total * (self.cost_sheet.ratio_value / 100)) + rec.budget_amount_total
                                        if rec.total > over_budget_limit:
                                            raise ValidationError(_("Limit for '%s' is '%s'" % (rec.variable.name, over_budget_limit)))
                                    return record.return_over_budget_confirmation()
                                if rec.total > rec.budget_amount_total:
                                    return record.return_over_budget_confirmation()
                            else:
                                if rec.total > rec.budget_amount_total:
                                    if record.cost_sheet.is_over_budget_ratio:
                                        over_budget_limit = (rec.budget_amount_total * (self.cost_sheet.ratio_value / 100)) + rec.budget_amount_total
                                        if rec.total > over_budget_limit:
                                            raise ValidationError(_("Limit for '%s' is '%s'" % (rec.variable.name, over_budget_limit)))
                                    return record.return_over_budget_confirmation()

                    elif record.budgeting_method == 'budget_type' and not record.is_continue_over_budget:
                        for rec in record.variable_line_ids:
                            record.validate_amount(rec)
                            if record.project_budget:
                                if self.total > self.cost_sheet.subcon_budget_left:
                                    if record.cost_sheet.is_over_budget_ratio:
                                        over_budget_limit = (self.cost_sheet.subcon_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.subcon_budget_left
                                        if self.total > over_budget_limit:
                                            raise ValidationError(_("Limit for '%s' is '%s'" % (rec.variable.name, over_budget_limit)))
                                    return record.return_over_budget_confirmation()
                                if self.total > self.project_budget.amount_left_subcon:
                                    if record.cost_sheet.is_over_budget_ratio:
                                        over_budget_limit = (self.project_budget.amount_left_subcon * (self.cost_sheet.ratio_value / 100)) + self.project_budget.amount_left_subcon
                                        if self.total > over_budget_limit:
                                            raise ValidationError(_("Limit for '%s' is '%s'" % (
                                            "Subcontractor", over_budget_limit)))
                                    return record.return_over_budget_confirmation()
                            else:
                                if self.total > self.cost_sheet.subcon_budget_left:
                                    if record.cost_sheet.is_over_budget_ratio:
                                        over_budget_limit = (self.project_budget.amount_left_subcon * (self.cost_sheet.ratio_value / 100)) + self.project_budget.amount_left_subcon
                                        if self.total > over_budget_limit:
                                            raise ValidationError(_("Limit for '%s' is '%s'" % (
                                            "Subcontractor", over_budget_limit)))
                                    return record.return_over_budget_confirmation()
                    else:
                        if not record.is_continue_over_budget:
                            if record.project_budget:
                                if self.total > self.cost_sheet.contract_budget_left:
                                    over_budget_limit = (self.cost_sheet.contract_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.contract_budget_left
                                    if self.total > over_budget_limit:
                                        raise ValidationError(_("Limit for this project is '%s'" % over_budget_limit))
                                    return record.return_over_budget_confirmation()
                                if self.total > self.project_budget.budget_left:
                                    over_budget_limit = (self.project_budget.budget_left * (self.cost_sheet.ratio_value / 100)) + self.project_budget.budget_left
                                    if self.total > over_budget_limit:
                                        raise ValidationError(_("Limit for this project is '%s'" % over_budget_limit))
                                    return record.return_over_budget_confirmation()
                            else:
                                if self.total > self.cost_sheet.contract_budget_left:
                                    if self.total > self.cost_sheet.contract_budget_left:
                                        over_budget_limit = (self.cost_sheet.contract_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.contract_budget_left
                                        if self.total > over_budget_limit:
                                            raise ValidationError(
                                                _("Limit for this project is '%s'" % over_budget_limit))
                                    return record.return_over_budget_confirmation()
                res = super(PurchaseOrderInherit, self).button_confirm()
                if self.sub_contracting == 'addendum':
                    if self.addendum_payment_method == 'join_payment':
                        claim = self.env['progressive.claim'].search([('progressive_bill', '=', True), ('project_id', '=', self.project.id), ('contract_parent_po', '=', self.contract_parent_po.id)], limit=1)
                        claim.write({
                            'related_contract_po_ids':  [(4, self.id)]
                        })
                    else:
                        claim = self.env['progressive.claim'].create({
                            'progressive_bill': True,
                            'project_id': self.project.id,
                            'contract_parent_po': self.id,
                            'state': 'in_progress',
                            'is_set_custom_claim': self.is_set_custom_claim,
                        })

                        if claim:
                            claim.sudo()._onchange_project_id()
                            claim.sudo()._onchange_contract_parent_po()
                            claim.sudo()._onchange_contract_parent_po_term()
                            claim.claim_confirm()
                else:
                    claim = self.env['progressive.claim'].create({
                        'progressive_bill': True,
                        'project_id': self.project.id,
                        'contract_parent_po': self.id,
                        'state': 'in_progress',
                        'is_set_custom_claim': self.is_set_custom_claim,
                    })

                    if claim:
                        claim.sudo()._onchange_project_id()
                        claim.sudo()._onchange_contract_parent_po()
                        claim.sudo()._onchange_contract_parent_po_term()
                        claim.claim_confirm()

                return res
        else:
            res = super(PurchaseOrderInherit, self).button_confirm()
            return res

    def button_done(self):
        for record in self:
            claim1 = self.env['progressive.claim'].search([('progressive_bill', '=', True), ('project_id', '=', record.project_id.id),('contract_parent_po', '=', record.id)], limit=1)
            claim2 = self.env['progressive.claim'].search([('progressive_bill', '=', True), ('project_id', '=', record.project_id.id),('contract_parent_po', '=', record.contract_parent_po.id)], limit=1)
            if record.is_subcontracting == True:
                if record.addendum_payment_method == 'split_payment': 
                    if len(claim1) == 0:
                        raise ValidationError(_("You haven't made a Progressive Claim to pay vendor.\nPlease create it first."))
                    elif claim1.state == 'done':
                        record.write({'state': 'done'})
                    elif claim1.state != 'done':
                        raise ValidationError(_("You have an Unfinished Progressive Claim."))
                elif record.addendum_payment_method == 'join_payment': 
                    if len(claim2) == 0:
                        raise ValidationError(_("You haven't made a Progressive Claim to pay vendor.\nPlease create it first."))
                    elif claim2.state == 'done':
                        record.write({'state': 'done'})
                    elif claim2.state != 'done':
                        raise ValidationError(_("You have an Unfinished Progressive Claim."))
             
                    
    def auto_cancel_po(self, po):
        res = super(PurchaseOrderInherit, self).auto_cancel_po(po)
        for purchase in po:
            if purchase.is_services_orders or purchase.is_subcontracting:
                if purchase.count_claim < 1:
                    purchase.write({'state': 'cancel'})
        return res
        
