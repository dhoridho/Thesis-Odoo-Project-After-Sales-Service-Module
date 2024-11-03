from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date


class SaleOrderConst(models.Model):
    _inherit = 'sale.order.const'

    claim_id = fields.Many2one('progressive.claim', string="Progressive Claim", ondelete='restrict')
    count_claim = fields.Integer(compute="_compute_count_claim", string="Claim")
    responsible = fields.Selection([('contractor', 'Contractor'), ('client', 'Client')], string='Responsible')
    reason = fields.Text(string='Reason')
    is_renewed = fields.Boolean(string='Is renewed', compute="_get_default_is_renewed")
    new_contract = fields.Many2one('sale.order.const', string="New Contract")
    contract_cancel_bool = fields.Boolean(string='Contract Cancel', compute="_get_default_form_project")

    @api.depends('project_id', 'contract_category')
    def _get_default_form_project(self):
        for rec in self:
            if rec.contract_category == 'main':
                if rec.project_id.primary_states == 'cancelled':
                    rec.contract_cancel_bool = True
                else:
                    rec.contract_cancel_bool = False
            else:
                so_var = self.env['variation.order.line'].search(
                    [('project_id', '=', rec.project_id.id), ('name', '=', rec.id), ('state', '=', 'cancel')], limit=1)
                if so_var:
                    rec.contract_cancel_bool = True
                else:
                    rec.contract_cancel_bool = False

    @api.depends('new_contract')
    def _get_default_is_renewed(self):
        for rec in self:
            if rec.new_contract:
                rec.is_renewed = True
            else:
                rec.is_renewed = False

    def create_renew_contract(self):
        if self.contract_category == 'var' and self.project_id.primary_states == 'cancelled':
            raise ValidationError(
                _("Cannot create a new contract for this project because the project has been cancelled"))
        else:
            renewed_contract = self.copy()
            renewed_contract.write({
                'state': 'draft',
                'state_1': 'draft',
                'sale_state': 'pending',
                'sale_state_1': 'pending',
                'use_retention': True,
                'use_dp': True,
                'boq_revised_bool': False,
                'approved_user_ids': False,
                'approved_user': False,
            })
            renewed_contract.sale_order_const_user_ids = [(5, 0, 0)]

            milestone_values = []
            i = 0

            # Copy milestone terms, append on first loop, add on second loop in order to make += works
            # Needed due to validation error on milestone terms
            if self.is_set_custom_claim:
                if len(self.milestone_term_ids) > 0:
                    for terms in self.milestone_term_ids:
                        if i == 0:
                            milestone_values.append(terms.copy())
                        else:
                            milestone_values[0] += terms.copy()
                        i += 1

                    renewed_contract.milestone_term_ids = milestone_values[0]

            for scope in self.project_scope_ids:
                renewed_contract.project_scope_ids += scope.copy()

            for section in self.section_ids:
                renewed_contract.section_ids += section.copy()

            for variable in self.variable_ids:
                renewed_contract.variable_ids += variable.copy()

            renewed_contract.onchange_approving_matrix_lines()

            self.write({
                'new_contract': renewed_contract.id,
            })

            return {
                'name': _(renewed_contract.name),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order.const',
                'res_id': renewed_contract.id,
                'target': 'current',
            }

    def _compute_count_claim(self):
        for res in self:
            claim = 0.0
            if res.vo_payment_type == 'split':
                claim = self.env['progressive.claim'].search_count(
                    [('progressive_bill', '=', False), ('project_id', '=', res.project_id.id),
                     ('contract_parent', '=', res.id)])
                res.write({'count_claim': claim})
            elif res.vo_payment_type == 'join':
                claim = self.env['progressive.claim'].search_count(
                    [('progressive_bill', '=', False), ('project_id', '=', res.project_id.id),
                     ('contract_parent', '=', res.contract_parent.id)])
                res.write({'count_claim': claim})
            return claim

    @api.onchange('milestone_term_ids')
    def _compute_claim(self):
        for res in self:
            claim = self.env['progressive.claim'].search(
                [('progressive_bill', '=', False), ('project_id', '=', res.project_id.id),
                 ('contract_parent', '=', res.contract_parent.id)], limit=1)
            if res.vo_payment_type == 'join':
                if res.contract_parent:
                    res.write({'claim_id': claim})
                else:
                    pass
            else:
                pass

    def action_progressive_claim(self):
        for res in self:
            if res.vo_payment_type == 'split':
                claim2 = self.env['progressive.claim'].search(
                    [('progressive_bill', '=', False), ('project_id', '=', res.project_id.id),
                     ('contract_parent', '=', res.id)], limit=1)
            elif res.vo_payment_type == 'join':
                claim2 = self.env['progressive.claim'].search(
                    [('progressive_bill', '=', False), ('project_id', '=', res.project_id.id),
                     ('contract_parent', '=', res.contract_parent.id)], limit=1)
            action = claim2.get_formview_action()
            return action

    def create_progressive_claim(self):
        if self.is_set_custom_claim == True and self.claim_type != False:
            context = {'default_progressive_bill': False,
                       'default_project_id': self.project_id.id,
                       'default_contract_parent': self.contract_parent.id,
                       'is_set_custom_claim': True,
                       }

        elif self.is_set_custom_claim == True and self.claim_type == False:
            context = {'default_progressive_bill': False,
                       'default_project_id': self.project_id.id,
                       'default_contract_parent': self.contract_parent.id,
                       'is_set_custom_claim': False,
                       }

        else:
            context = {'default_progressive_bill': False,
                       'default_project_id': self.project_id.id,
                       'default_contract_parent': self.contract_parent.id,
                       'is_set_custom_claim': False,
                       }

        return {
            "name": "Progressive Claim",
            "type": "ir.actions.act_window",
            "res_model": "progressive.claim",
            "context": context,
            "view_mode": 'form',
            "target": "current",
        }

    def _button_confirm_contd(self):
        res = super(SaleOrderConst, self)._button_confirm_contd()
        if self.contract_category == 'main':
            claim = self.env['progressive.claim'].create({
                'progressive_bill': False,
                'project_id': self.project_id.id,
                'contract_parent': self.id,
                'state': 'in_progress',
                'is_set_custom_claim': self.is_set_custom_claim,
            })

            if claim:
                claim.sudo()._onchange_project_id()
                claim.sudo()._onchange_contract_parent()
                claim.sudo()._onchange_contract_parent_term()
                claim.claim_confirm()

        elif self.contract_category == 'var':
            if self.vo_payment_type == 'split':
                claim = self.env['progressive.claim'].create({
                    'progressive_bill': False,
                    'project_id': self.project_id.id,
                    'contract_parent': self.id,
                    'state': 'in_progress',
                    'is_set_custom_claim': self.is_set_custom_claim,
                })

                if claim:
                    claim.sudo()._onchange_project_id()
                    claim.sudo()._onchange_contract_parent()
                    claim.sudo()._onchange_contract_parent_term()
                    claim.claim_confirm()
        return res

    def _split_payment_type(self, contract_list):
        res = super(SaleOrderConst, self)._split_payment_type(contract_list)
        # if self.is_set_custom_claim == True and self.claim_type != False:
        #     claim = self.env['progressive.claim'].create({
        #         'progressive_bill': False,
        #         'project_id': self.project_id.id,
        #         'contract_parent': self.id,
        #         'state': 'in_progress',
        #         'is_set_custom_claim': self.is_set_custom_claim,
        #     })
        #
        #     if claim:
        #         claim.sudo()._onchange_project_id()
        #         claim.sudo()._onchange_contract_parent()
        #         claim.sudo()._onchange_contract_parent_term()
        #         claim.claim_confirm()
        return res

    def _join_payment_type(self, contract_list):
        res = super(SaleOrderConst, self)._join_payment_type(contract_list)
        if self.contract_parent:
            claim = self.env['progressive.claim'].search(
                [('progressive_bill', '=', False), ('project_id', '=', self.project_id.id),
                 ('contract_parent', '=', self.contract_parent.id)], limit=1)
            claim.write({'related_contract_so_ids': [(4, self.id)]})
        return res

    def action_done(self):
        for record in self:
            claim1 = self.env['progressive.claim'].search(
                [('progressive_bill', '=', False), ('project_id', '=', record.project_id.id),
                 ('contract_parent', '=', record.id)], limit=1)
            claim2 = self.env['progressive.claim'].search(
                [('progressive_bill', '=', False), ('project_id', '=', record.project_id.id),
                 ('contract_parent', '=', record.contract_parent.id)], limit=1)
            if record.vo_payment_type == 'split':
                if len(claim1) == 0:
                    raise ValidationError(
                        _("You haven't made a Progressive Claim to receive payment.\nPlease create it first."))
                elif claim1.state == 'done':
                    record.write({'state': 'done', 'sale_state': 'done'})
                elif claim1.state != 'done':
                    raise ValidationError(_("You have an Unfinished Progressive Claim."))
            elif record.vo_payment_type == 'join':
                if len(claim2) == 0:
                    raise ValidationError(
                        _("You haven't made a Progressive Claim to receive payment.\nPlease create it first."))
                elif claim2.state == 'done':
                    record.write({'state': 'done', 'sale_state': 'done'})
                elif claim2.state != 'done':
                    raise ValidationError(_("You have an Unfinished Progressive Claim."))


class VariationOrderLineInherit2(models.Model):
    _inherit = "variation.order.line"

    claim_id = fields.Many2one('progressive.claim', string="Progressive Claim", ondelete='cascade')
