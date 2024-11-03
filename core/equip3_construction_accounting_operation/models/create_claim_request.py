from odoo import _, api, fields, models
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError


class CreateClaimRequest(models.Model):
    _name = 'claim.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Claim Request'
    _check_company_auto = True

    def send_request(self):
        if self.progressive_claim_id:
            progressive_claim_id = self.progressive_claim_id
        else:
            progressive_claim_id = self.env['progressive.claim'].browse(self.env.context.get('active_id'))

        progressive_claim_id.write({
            'po_subcon_line_id': self.po_subcon_line_id.id or False,
        })

        if self.request_for == 'progress':
            if not self.request_line_ids:
                raise ValidationError(_("Add at least one job order to confirm."))

        if self.progressive_bill is False:
            if self.request_for == 'progress':
                if not self.progressive_claim_id.project_id.down_payment_id:
                    raise ValidationError("Set account for down payment receivable first.")
                if not self.progressive_claim_id.project_id.accrued_id:
                    raise ValidationError("Set account for claim request receivable first.")
                if not self.progressive_claim_id.project_id.retention_id:
                    raise ValidationError("Set account for retention receivable first.")
                if not self.progressive_claim_id.project_id.revenue_id:
                    raise ValidationError("Set account for revenue first.")
        else:
            if self.request_for == 'progress':
                if not self.progressive_claim_id.project_id.down_payment_account:
                    raise ValidationError("Set account for down payment payable first.")
                if not self.progressive_claim_id.project_id.accrued_account:
                    raise ValidationError("Set account for claim request payable first.")
                if not self.progressive_claim_id.project_id.retention_account:
                    raise ValidationError("Set account for retention payable first.")
                if not self.progressive_claim_id.project_id.cost_account:
                    raise ValidationError("Set account for cost of revenue first.")

        res = self.request_line_ids
        request_line = []
        for request in res:
            if progressive_claim_id.progressive_bill:
                request_line.append(
                    (0, 0, {'work_order': request.work_order and request.work_order.id or False,
                            'work_order_sub': request.work_order_sub and request.work_order_sub.id or False,
                            'stage_new': request.stage_new and request.stage_new.id or False,
                            'assigned_to': request.assigned_to and request.assigned_to.id or False,
                            'completion_date': request.completion_date,
                            'stage_weightage': request.stage_weightage,
                            'work_subcon_weightage': request.work_subcon_weightage,
                            'work_weightage': request.work_weightage,
                            'last_progress': request.last_progress,
                            'task_contract_po': request.work_order_sub.purchase_subcon.id,
                            'wo_prog_temp': request.wo_prog_temp,
                            'work_progress': request.work_progress,
                            'progress': request.progress,
                            'progressive_bill': request.progressive_bill
                            }
                     ))
            else:
                request_line.append(
                    (0, 0, {'work_order': request.work_order and request.work_order.id or False,
                            'work_order_sub': request.work_order_sub and request.work_order_sub.id or False,
                            'stage_new': request.stage_new and request.stage_new.id or False,
                            'assigned_to': request.assigned_to and request.assigned_to.id or False,
                            'completion_date': request.completion_date,
                            'stage_weightage': request.stage_weightage,
                            'work_subcon_weightage': request.work_subcon_weightage,
                            'work_weightage': request.work_weightage,
                            'last_progress': request.last_progress,
                            'wo_prog_temp': request.wo_prog_temp,
                            'work_progress': request.work_progress,
                            'progress': request.progress,
                            'progressive_bill': request.progressive_bill
                            }
                     ))

        if self.is_claim_request_approval_matrix is False:

            cr_line = self.env['claim.request.line'].sudo().create({
                'name': self.name,
                'claim_id': progressive_claim_id.id or False,
                'request_for': self.request_for,
                'progressive_bill': self.progressive_bill,
                'partner_request_id': self.partner_request_id.id or False,
                'create_uid': self.create_uid.id or False,
                'create_date': datetime.now(),
                'requested_progress': self.requested_progress,
                'approved_progress': self.requested_progress,
                'requested_progress_2': self.requested_progress,
                'contract_amount': self.contract_amount,
                'down_payment': self.down_payment,
                'dp_amount': self.dp_amount,
                'retention1': self.retention1,
                'retention2': self.retention2,
                'retention1_amount': self.retention1_amount,
                'retention2_amount': self.retention2_amount,
                'amount_approved': self.amount_approved,
                'max_claim': self.max_claim,
                'last_progress': self.last_progress,
                'account_1': self.account_1,
                'account_2': self.account_2,
                'account_3': self.account_3,
                'account_4': self.account_4,
                'state': 'approved',
                'request_ids': request_line,
                'request_id': self.id,
            })

            if self.progressive_claim_id.progressive_bill is False:

                debit_account_1 = self.project_id.accrued_id.id
                debit_account_2 = self.project_id.down_payment_id.id
                debit_account_3 = self.project_id.retention_id.id
                debit_account_4 = self.project_id.cost_account.id
                credit_account = self.project_id.revenue_id.id
                credit_account_2 = self.project_id.cip_account_id.id

                sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
                sequence_pool = self.env['ir.sequence']

                cip_account_move = self.env['account.move'].search(
                    [('analytic_group_ids', 'in', self.progressive_claim_id.analytic_idz.ids), ('state', '=', 'posted')])
                cip_debit_amount = 0
                cip_credit_amount = 0
                for cip_account in cip_account_move:
                    for line in cip_account.line_ids:
                        if line.debit > 0 and line.account_id.name == "Construction In Progress":
                            cip_debit_amount += line.debit
                        elif line.credit > 0 and line.account_id.name == "Construction In Progress":
                            cip_credit_amount += line.credit

                cost_in_progress_amount = cip_debit_amount - cip_credit_amount
                cost_amount = cost_in_progress_amount

                # create journal entry on account.move
                account_journal_entry = self.env['account.move'].create({
                    'name': sequence_pool.sudo().get_id(sequence_id.id),
                    'journal_claim_id': self.progressive_claim_id.id,
                    'project_id': self.project_id.id,
                    'contract_parent': self.contract_parent.id,
                    'request_id': cr_line.id,
                    'analytic_group_ids': self.progressive_claim_id.analytic_idz.ids,
                    'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
                    'ref': 'Claim Request - ' + self.name,
                    'date': datetime.now(),
                })

                accrued_amount = abs(self.account_1)
                unearned_amount = abs(self.account_2)
                retention_amount = abs(self.account_3)
                credit_amount = abs(self.account_4)

                journal_items = []
                for i in range(6):
                    # 0 = credit, 1 = debit 1 (accrued), 2 = debit 2 (unearned)
                    if i == 0:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Claim Request - ' + self.name,
                            'account_id': credit_account,
                            'analytic_tag_ids': self.progressive_claim_id.analytic_idz.ids,
                            'amount_currency': -credit_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': credit_amount,
                        }))
                    elif i == 1:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Claim Request - ' + self.name,
                            'account_id': debit_account_1,
                            'analytic_tag_ids': self.progressive_claim_id.analytic_idz.ids,
                            'amount_currency': accrued_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': accrued_amount,
                            'credit': 0.0,
                        }))
                    elif i == 2:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Claim Request - ' + self.name,
                            'account_id': debit_account_2,
                            'analytic_tag_ids': self.progressive_claim_id.analytic_idz.ids,
                            'amount_currency': unearned_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': unearned_amount,
                            'credit': 0.0,
                        }))
                    elif i == 3:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Claim Request - ' + self.name,
                            'account_id': debit_account_3,
                            'analytic_tag_ids': self.progressive_claim_id.analytic_idz.ids,
                            'amount_currency': retention_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': retention_amount,
                            'credit': 0.0,
                        }))
                    elif i == 4:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Claim Request - ' + self.name,
                            'account_id': debit_account_4,
                            'analytic_tag_ids': self.progressive_claim_id.analytic_idz.ids,
                            'amount_currency': cost_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': cost_amount,
                            'credit': 0.0,
                        }))
                    elif i == 5:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Claim Request - ' + self.name,
                            'account_id': credit_account_2,
                            'analytic_tag_ids': self.progressive_claim_id.analytic_idz.ids,
                            'amount_currency': -cost_in_progress_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': cost_in_progress_amount,
                        }))

                account_journal_entry.line_ids = journal_items

                # create journal entry on project.journal.entry object on progressive claim
                claim_journal_entry = self.env['project.journal.entry'].create({
                    'name': account_journal_entry.name,
                    'journal_claim_id': self.progressive_claim_id.id,
                    'project_id': self.project_id.id,
                    'contract_parent': self.contract_parent.id,
                    'company_id': self.progressive_claim_id.company_id.id,
                    'branch_id': self.progressive_claim_id.branch_id.id,
                    'request_id': cr_line.id,
                    'analytic_group_ids': self.progressive_claim_id.analytic_idz.ids,
                    'journal_id': account_journal_entry.journal_id.id,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'ref': 'Claim Request - ' + self.name,
                    'date': datetime.now(),
                    'period_id': account_journal_entry.period_id.id,
                    'fiscal_year': account_journal_entry.fiscal_year.id,
                })

                # credit line
                claim_journal_entry.line_ids.create({
                    'journal_entry_id': claim_journal_entry.id,
                    'account_id': credit_account,
                    'name': claim_journal_entry.ref,
                    'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                    'amount_currency': -credit_amount,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'debit': 0.0,
                    'credit': credit_amount,
                })

                # credit line
                claim_journal_entry.line_ids.create({
                    'journal_entry_id': claim_journal_entry.id,
                    'account_id': credit_account_2,
                    'name': claim_journal_entry.ref,
                    'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                    'amount_currency': -cost_in_progress_amount,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'debit': 0.0,
                    'credit': cost_in_progress_amount,
                })

                # debit line 1 (accrued)
                claim_journal_entry.line_ids.create({
                    'journal_entry_id': claim_journal_entry.id,
                    'account_id': debit_account_1,
                    'name': claim_journal_entry.ref,
                    'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                    'amount_currency': accrued_amount,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'debit': accrued_amount,
                    'credit': 0.0,
                })

                # debit line 2 (unearned)
                claim_journal_entry.line_ids.create({
                    'journal_entry_id': claim_journal_entry.id,
                    'account_id': debit_account_2,
                    'name': claim_journal_entry.ref,
                    'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                    'amount_currency': unearned_amount,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'debit': unearned_amount,
                    'credit': 0.0,
                })

                # debit line 3 (retention)
                claim_journal_entry.line_ids.create({
                    'journal_entry_id': claim_journal_entry.id,
                    'account_id': debit_account_3,
                    'name': claim_journal_entry.ref,
                    'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                    'amount_currency': retention_amount,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'debit': retention_amount,
                    'credit': 0.0,
                })

                # debit line 4 (cost)
                claim_journal_entry.line_ids.create({
                    'journal_entry_id': claim_journal_entry.id,
                    'account_id': debit_account_4,
                    'name': claim_journal_entry.ref,
                    'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                    'amount_currency': cost_amount,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'debit': cost_amount,
                    'credit': 0.0,
                })

            elif self.progressive_claim_id.progressive_bill is True:

                cost_of_revenue_amount = abs(self.account_4)
                advance_amount = abs(self.account_2)
                retention_amount = abs(self.account_3)
                contract_liabilities_amount = abs(self.account_1)

                debit_account = self.progressive_claim_id.project_id.cip_account_id.id if self.progressive_claim_id.project_id.cip_account_id else self.progressive_claim_id.project_id.cost_account.id
                credit_account_1 = self.progressive_claim_id.project_id.down_payment_account.id
                credit_account_2 = self.progressive_claim_id.project_id.accrued_account.id
                credit_account_3 = self.progressive_claim_id.project_id.retention_account.id

                sequence_id = self.env['ir.sequence'].search([('code', '=', 'jurnal.claim.request.sequence')])
                sequence_pool = self.env['ir.sequence']

                # create journal entry on account.move object
                account_journal_entry = self.env['account.move'].create({
                    'name': sequence_pool.sudo().get_id(sequence_id.id),
                    'journal_id': self.env['account.journal'].search([('name', '=', 'Claim Request')]).id,
                    'project_id': self.project_id.id,
                    'contract_parent': self.contract_parent.id,
                    'contract_parent_po': self.contract_parent_po.id,
                    'request_id': cr_line.id,
                    'analytic_group_ids': self.progressive_claim_id.analytic_idz.ids,
                    'journal_claim_id': self.progressive_claim_id.id,
                    'ref': 'Claim Request - ' + self.name,
                    'date': datetime.now(),
                })

                journal_items = []
                for i in range(4):
                    # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities)
                    if i == 0:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'account_id': debit_account,
                            'name': account_journal_entry.ref,
                            'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                            'amount_currency': cost_of_revenue_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': cost_of_revenue_amount,
                            'credit': 0.0,
                        }))
                    elif i == 1:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'account_id': credit_account_1,
                            'name': account_journal_entry.ref,
                            'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                            'amount_currency': -advance_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': advance_amount,
                        }))
                    elif i == 2:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'account_id': credit_account_2,
                            'name': account_journal_entry.ref,
                            'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                            'amount_currency': -contract_liabilities_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': contract_liabilities_amount,
                        }))
                    elif i == 3:
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'account_id': credit_account_3,
                            'name': account_journal_entry.ref,
                            'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                            'amount_currency': -retention_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': retention_amount,
                        }))

                account_journal_entry.line_ids = journal_items

                # create journal entry on project.journal.entry object on progressive claim

                claim_journal_entry = self.env['project.journal.entry'].create({
                    'name': account_journal_entry.name,
                    'journal_claim_id': self.progressive_claim_id.id,
                    'project_id': self.project_id.id,
                    'contract_parent': self.contract_parent.id,
                    'contract_parent_po': self.contract_parent_po.id,
                    'company_id': self.progressive_claim_id.company_id.id,
                    'branch_id': self.progressive_claim_id.branch_id.id,
                    'request_id': cr_line.id,
                    'analytic_group_ids': self.progressive_claim_id.analytic_idz.ids,
                    'journal_id': account_journal_entry.journal_id.id,
                    'currency_id': self.progressive_claim_id.company_currency_id.id,
                    'ref': 'Claim Request - ' + self.name,
                    'date': datetime.now(),
                    'period_id': account_journal_entry.period_id.id,
                    'fiscal_year': account_journal_entry.fiscal_year.id,
                })

                claim_journal_items = []
                for i in range(4):
                    # 0 = debit, 1 = credit (advance), 2 = credit (contract liabilities)
                    if i == 0:
                        claim_journal_items.append((0, 0, {
                            'journal_entry_id': claim_journal_entry.id,
                            'account_id': debit_account,
                            'name': claim_journal_entry.ref,
                            'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                            'amount_currency': cost_of_revenue_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': cost_of_revenue_amount,
                            'credit': 0.0,
                        }))
                    elif i == 1:
                        claim_journal_items.append((0, 0, {
                            'journal_entry_id': claim_journal_entry.id,
                            'account_id': credit_account_1,
                            'name': claim_journal_entry.ref,
                            'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                            'amount_currency': -advance_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': advance_amount,
                        }))
                    elif i == 2:
                        claim_journal_items.append((0, 0, {
                            'journal_entry_id': claim_journal_entry.id,
                            'account_id': credit_account_2,
                            'name': claim_journal_entry.ref,
                            'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                            'amount_currency': -contract_liabilities_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': contract_liabilities_amount,
                        }))
                    elif i == 3:
                        claim_journal_items.append((0, 0, {
                            'journal_entry_id': claim_journal_entry.id,
                            'account_id': credit_account_3,
                            'name': claim_journal_entry.ref,
                            'analytic_tag_ids': claim_journal_entry.analytic_group_ids.ids,
                            'amount_currency': -retention_amount,
                            'currency_id': self.progressive_claim_id.company_currency_id.id,
                            'debit': 0.0,
                            'credit': retention_amount,
                        }))

                claim_journal_entry.line_ids = claim_journal_items


        elif self.is_claim_request_approval_matrix is True:

            if len(self.approval_matrix_ids) == 0:
                raise ValidationError(
                    _("There's no claim request approval matrix for this project or approval matrix default created. You have to create it first."))

            cr_line = self.env['claim.request.line'].sudo().create({
                'name': self.name,
                'claim_id': progressive_claim_id.id or False,
                'request_for': self.request_for,
                'progressive_bill': self.progressive_bill,
                'partner_request_id': self.partner_request_id.id or False,
                'create_uid': self.create_uid.id or False,
                'create_date': datetime.now(),
                'requested_progress': self.requested_progress,
                'requested_progress_2': self.requested_progress,
                'contract_amount': self.contract_amount,
                'down_payment': self.down_payment,
                'dp_amount': self.dp_amount,
                'retention1': self.retention1,
                'retention2': self.retention2,
                'retention1_amount': self.retention1_amount,
                'retention2_amount': self.retention2_amount,
                'amount_approved': self.amount_approved,
                'max_claim': self.max_claim,
                'last_progress': self.last_progress,
                'account_1': self.account_1,
                'account_2': self.account_2,
                'account_3': self.account_3,
                'account_4': self.account_4,
                'state': 'to_approve',
                # 'employee_id': self.env.user.id,
                'request_ids': request_line,
                'request_id': self.id
            })

            cr_line.sudo()._compute_is_customer_approval_matrix()
            cr_line.sudo()._compute_approving_customer_matrix()
            cr_line.sudo().onchange_approving_matrix_lines()
            cr_line.sudo().action_request_for_approving_matrix()

            action_id = self.env.ref('equip3_construction_accounting_operation.progressive_claim_action')
            template_id = self.env.ref(
                'equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(self.progressive_claim_id.id) + '&action=' + str(
                action_id.id) + '&view_type=form&model=progressive.claim'

            if self.approval_matrix_ids and len(self.approval_matrix_ids[0].approvers) > 1:
                for approved_matrix_id in self.approval_matrix_ids[0].approvers:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'url': url,
                        'code': self.name,
                    }
                    template_id.with_context(ctx).send_mail(self.progressive_claim_id.id, True)
                    # template_id.with_context(ctx).send_mail(cr_line.id, True)
            else:
                approver = self.approval_matrix_ids[0].approvers[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'url': url,
                    'code': self.name,
                }
                template_id.with_context(ctx).send_mail(self.progressive_claim_id.id, True)
                # template_id.with_context(ctx).send_mail(cr_line.id, True)

            # action_id = self.env.ref('equip3_construction_accounting_operation.claim_request_action')
            # template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval')
            # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            # url = base_url + '/web#id=' + str(cr_line.id) + '&action='+ str(action_id.id) + '&view_type=form&model=claim.request.line'
            # if self.approval_matrix_ids and len(self.approval_matrix_ids[0].approvers) > 1:
            #     for approved_matrix_id in self.approval_matrix_ids[0].approvers:
            #         approver = approved_matrix_id
            #         ctx = {
            #             'email_from' : self.env.user.company_id.email,
            #             'email_to' : approver.partner_id.email,
            #             'approver_name' : approver.name,
            #             'date': date.today(),
            #             'url' : url,
            #         }
            #         template_id.with_context(ctx).send_mail(cr_line.id, force_send=True)
            #         template_id.with_context(ctx).send_mail(self.progressive_claim_id.id, force_send=True)
            # else:
            #     approver = self.approval_matrix_ids[0].approvers[0]
            #     ctx = {
            #         'email_from' : self.env.user.company_id.email,
            #         'email_to' : approver.partner_id.email,
            #         'approver_name' : approver.name,
            #         'date': date.today(),
            #         'url' : url,
            #     }
            #     template_id.with_context(ctx).send_mail(cr_line.id, force_send=True)
            #     template_id.with_context(ctx).send_mail(self.progressive_claim_id.id, force_send=True)

            # action_id = self.env.ref('equip3_construction_accounting_operation.claim_request_action')
            # template_id = self.env.ref('equip3_construction_accounting_operation.email_template_reminder_for_claim_request_approval')
            # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            # url = base_url + '/web#id=' + str(cr_line.id) + '&action='+ str(action_id.id) + '&view_type=form&model=claim.request.line'

            # if self.approval_matrix_ids and len(self.approval_matrix_ids[0].approvers) > 1:
            #     for approved_matrix_id in self.approval_matrix_ids[0].approvers:
            #         approver = approved_matrix_id
            #         ctx = {
            #             'email_from' : self.env.user.company_id.email,
            #             'email_to' : approver.partner_id.email,
            #             'approver_name' : approver.name,
            #             'date': date.today(),
            #             'url' : url,
            #             'code' : self.name,
            #         }
            #         template_id.with_context(ctx).send_mail(self.progressive_claim_id.id, True)
            #         template_id.with_context(ctx).send_mail(cr_line.id, True)
            # else:
            #     approver = self.approval_matrix_ids[0].approvers[0]
            #     ctx = {
            #         'email_from' : self.env.user.company_id.email,
            #         'email_to' : approver.partner_id.email,
            #         'approver_name' : approver.name,
            #         'date': date.today(),
            #         'url' : url,
            #         'code' : self.name,
            #     }
            #     template_id.with_context(ctx).send_mail(self.progressive_claim_id.id, True)
            #     template_id.with_context(ctx).send_mail(cr_line.id, True)

            # using_approving_matrix_user = False
            # if cr_line.is_claim_request_approval_matrix:
            #     if cr_line.approving_matrix_sale_id:
            #         if len(cr_line.approving_matrix_sale_id.approver_matrix_line_ids) > 0:
            #             using_approving_matrix_user = True
            #             for user in cr_line.approving_matrix_sale_id.approver_matrix_line_ids[0].user_name_ids:
            #                 base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            #                 url = base_url + '/web#id=' + str(cr_line.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
            #                 ctx = {
            #                     'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
            #                     'email_to' : user.partner_id.email,
            #                     'approver_name' : user.partner_id.name,
            #                     'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
            #                     'url' : url,
            #                     'cr_name': cr_line.request_id.name
            #                 }
            #                 template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)

            # if not using_approving_matrix_user:
            #     for user in self.project_director:
            #         base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            #         url = base_url + '/web#id=' + str(progressive_claim_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=progressive.claim'
            #         ctx = {
            #             'email_from' : self.env['res.partner'].search([('name', '=', 'System Notification')]).email,
            #             'email_to' : user.partner_id.email,
            #             'approver_name' : user.partner_id.name,
            #             'date': (datetime.today() + timedelta(hours=7)).strftime("%m/%d/%Y, %H:%M:%S"),
            #             'url' : url,
            #             'cr_name': cr_line.request_id.name
            #         }
            #         template_id.sudo().with_context(ctx).send_mail(self.progressive_claim_id.id, True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('claim.request.sequence') or '/'
        res = super(CreateClaimRequest, self).create(vals)
        return res

    name = fields.Char(string='Number', copy=False, required=True, readonly=True,
                       index=True, default=lambda self: _('New'))

    request_for = fields.Selection([
        ('down_payment', 'Down Payment'),
        ('progress', 'Progress'),
        ('retention1', 'Retention 1'),
        ('retention2', 'Retention 2')
    ], string='Requested Type', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    project_id = fields.Many2one('project.project', 'Project')
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        change_default=True, index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_request_id = fields.Many2one(
        'res.partner', string='Request Address',
        change_default=True, index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    vendor = fields.Many2one(
        'res.partner', string='Vendor',
        change_default=True, index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    branch_id = fields.Many2one(related="progressive_claim_id.branch_id", string="Branch")
    create_uid = fields.Many2one('res.users', index=True, readonly=True, default=lambda self: self.env.user)
    create_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    project_director = fields.Many2one('res.users', string='Project Manager')
    requested_progress = fields.Float(string='Requested Progress', digits=(2, 2))
    requested_amount = fields.Float(string='Requested Amount')
    contract_amount = fields.Float(string='Contract Amount')
    down_payment = fields.Float(string="Down Payment")
    dp_amount = fields.Float(string="Amount")
    retention1 = fields.Float(string="Retention 1")
    retention2 = fields.Float(string="Retention 2")
    retention1_amount = fields.Float(string="Amount")
    retention2_amount = fields.Float(string="Amount")
    request_line_ids = fields.One2many('const.request.line', 'request_id', string="Request Lines")
    progressive_claim_id = fields.Many2one('progressive.claim', string="Progressive Claim")
    progressive_bill = fields.Boolean('Progressive Bill', default=False)
    contract_parent = fields.Many2one('sale.order.const', string="Parent Contract")
    contract_parent_po = fields.Many2one('purchase.order', string="Parent Contract")
    perc_approved = fields.Float(string='Approved Amount', compute="_temp_amount_calculation")
    amount_approved = fields.Float(string='Approved Amount', compute="_temp_amount_calculation")
    max_claim = fields.Float(string="Maximum Claim Amount", compute="_max_claim_calculation")
    max_percen = fields.Float(string="Maximum Percentage", compute="_max_claim_calculation")
    gross_amount = fields.Float(string="Gross Amount", compute="_max_claim_calculation")
    dp = fields.Float(string="Down Payment Amount", compute="_max_claim_calculation")
    reten = fields.Float(string="Retention Amount", compute="_max_claim_calculation")
    remaining_request = fields.Float(string="Remaining Request", compute="_remaining_request_calculation")
    last_progress = fields.Float(string="Last Progress")
    account_1 = fields.Float(string="Account 1", compute="_compute_account_1", store=True)
    account_2 = fields.Float(string="Account 2", compute="_compute_account_2", store=True)
    account_3 = fields.Float(string="Account 3", compute="_compute_account_3", store=True)
    account_4 = fields.Float(string="Account 4", compute="_compute_account_4", store=True)
    is_claim_request_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                      compute='_compute_is_customer_approval_matrix')
    approving_matrix_sale_id = fields.Many2one('approval.matrix.claim.request', string="Approval Matrix",
                                               compute='_compute_approving_customer_matrix', store=True)
    approval_matrix_ids = fields.One2many('approval.matrix.claim.request.line', 'order_id_wiz', store=True,
                                          string="Approved Matrix", compute='_compute_approving_matrix_lines')
    is_approval_matrix_filled = fields.Boolean(string="Custome Matrix", store=False)
    po_subcon_line_id = fields.Many2one('rfq.variable.line', string="Purchase Order Subcon Line", compute='_compute_po_subcon_line_id')

    @api.depends('request_line_ids')
    def _compute_po_subcon_line_id(self):
        for rec in self:
            if len(rec.request_line_ids)>0:
                rec.po_subcon_line_id = rec.request_line_ids[0].work_order_sub.po_subcon_id.id
            else:
                rec.po_subcon_line_id = False

    @api.depends('project_id')
    def _compute_is_customer_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_claim_request_approval_matrix = IrConfigParam.get_param('is_claim_request_approval_matrix')
        for record in self:
            record.is_claim_request_approval_matrix = is_claim_request_approval_matrix

    @api.depends('project_id', 'branch_id', 'company_id', 'progressive_bill')
    def _compute_approving_customer_matrix(self):
        for record in self:
            record.approving_matrix_sale_id = False
            if record.is_claim_request_approval_matrix:
                if record.progressive_bill == False:
                    approving_matrix_sale_id = self.env['approval.matrix.claim.request'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('project_id', 'in', (record.project_id.id)),
                        ('progressive_bill', '=', False),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.claim.request'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('set_default', '=', True),
                        ('progressive_bill', '=', False)], limit=1)

                else:
                    approving_matrix_sale_id = self.env['approval.matrix.claim.request'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('project_id', 'in', (record.project_id.id)),
                        ('progressive_bill', '=', True),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.claim.request'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('set_default', '=', True),
                        ('progressive_bill', '=', True)], limit=1)

                if approving_matrix_sale_id:
                    record.approving_matrix_sale_id = approving_matrix_sale_id and approving_matrix_sale_id.id or False
                else:
                    if approving_matrix_default:
                        record.approving_matrix_sale_id = approving_matrix_default and approving_matrix_default.id or False

    @api.depends('approving_matrix_sale_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.is_claim_request_approval_matrix:
                counter = 1
                record.approval_matrix_ids = []
                if record.approving_matrix_sale_id:
                    for rec in record.approving_matrix_sale_id:
                        for line in rec.approval_matrix_ids:
                            data.append((0, 0, {
                                'sequence': counter,
                                'approvers': [(6, 0, line.approvers.ids)],
                                'minimum_approver': line.minimum_approver,
                            }))
                            counter += 1
                    record.approval_matrix_ids = data
                else:
                    record.approval_matrix_ids = False

    @api.depends('request_for', 'requested_progress', 'contract_amount')
    def _compute_account_4(self):
        for res in self:
            account_4 = 0
            if res.request_for == 'progress':
                if res.requested_progress > 0:
                    account_4 = res.contract_amount * ((res.requested_progress) / 100)
                    res.account_4 = account_4
                else:
                    pass
            else:
                pass

    @api.depends('request_for', 'requested_progress', 'contract_amount', 'retention1', 'retention2')
    def _compute_account_3(self):
        for res in self:
            account_3 = 0
            if res.request_for == 'progress':
                account_3 = (res.contract_amount * ((res.requested_progress) / 100)) * (
                            (res.retention1 + res.retention2) / 100)
                res.account_3 = account_3
            else:
                pass

    @api.depends('request_for', 'requested_progress', 'contract_amount', 'dp_amount')
    def _compute_account_2(self):
        for res in self:
            account_2 = 0
            if res.request_for == 'progress':
                if res.requested_progress > 0:
                    account_2 = res.dp_amount * (res.requested_progress / 100)
                    res.account_2 = account_2
                else:
                    pass
            else:
                pass

    @api.depends('request_for', 'requested_progress', 'account_4', 'account_3', 'account_2')
    def _compute_account_1(self):
        for res in self:
            account_1 = 0
            if res.request_for == 'progress':
                if res.requested_progress > 0:
                    account_1 = res.account_4 - res.account_3 - res.account_2
                    res.account_1 = account_1
                else:
                    pass
            else:
                pass

    # @api.depends('approving_matrix_sale_id')
    # def _compute_approval_matrix_filled(self):
    #     for record in self:
    #         record.is_approval_matrix_filled = False
    #         if record.approving_matrix_sale_id:
    #             record.is_approval_matrix_filled = True

    # @api.onchange('project_id')
    # def onchange_partner_id_new(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.onchange('request_id')
    # def _onchange_sale_name(self):
    #     self._compute_is_customer_approval_matrix()
    #     self._compute_approval_matrix_filled()

    # @api.depends('project_id','branch_id','company_id','progressive_bill')
    # def _compute_approving_customer_matrix(self):
    #     for record in self:
    #         record.approving_matrix_sale_id = False
    #         if record.is_claim_request_approval_matrix:
    #             if record.progressive_bill == False:
    #                 approving_matrix_sale_id = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('project_id', 'in', (record.project_id.id)),  
    #                                             ('progressive_bill', '=', False), 
    #                                             ('set_default', '=', False)], limit=1)

    #                 approving_matrix_default = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('set_default', '=', True),
    #                                             ('progressive_bill', '=', False)], limit=1)

    #             else:
    #                 approving_matrix_sale_id = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('project_id', 'in', (record.project_id.id)),  
    #                                             ('progressive_bill', '=', True), 
    #                                             ('set_default', '=', False)], limit=1)

    #                 approving_matrix_default = self.env['approval.matrix.claim.request'].search([
    #                                             ('company_id', '=', record.company_id.id),
    #                                             ('branch_id', '=', record.branch_id.id), 
    #                                             ('set_default', '=', True),
    #                                             ('progressive_bill', '=', True)], limit=1)

    #             if approving_matrix_sale_id:
    #                 record.approving_matrix_sale_id = approving_matrix_sale_id and approving_matrix_sale_id.id or False
    #             else:
    #                 if approving_matrix_default:
    #                     record.approving_matrix_sale_id = approving_matrix_default and approving_matrix_default.id or False

    # @api.depends('approving_matrix_sale_id')
    # def _compute_approving_matrix_lines(self):
    #     data = [(5, 0, 0)]
    #     for record in self:
    #         if record.is_claim_request_approval_matrix:
    #             record.approved_matrix_ids = []
    #             counter = 1
    #             record.approved_matrix_ids = []
    #             for rec in record.approving_matrix_sale_id:
    #                 for line in rec.approver_matrix_line_ids:
    #                     data.append((0, 0, {
    #                         'sequence': counter,
    #                         'user_name_ids': [(6, 0, line.user_name_ids.ids)],
    #                         'minimum_approver': line.minimum_approver,
    #                     }))
    #                     counter += 1
    #             record.approved_matrix_ids = data

    def _temp_amount_calculation(self):
        for res in self:
            if res.request_for == 'down_payment':
                request_dp = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'down_payment'),
                     ('state', '=', 'approved')])
                if len(request_dp) > 0:
                    res.amount_approved = sum(request_dp.mapped('max_claim'))
                else:
                    res.amount_approved = 0
            elif res.request_for == 'progress':
                request_progress = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'progress'),
                     ('state', '=', 'approved')])
                if len(request_progress) > 0:
                    res.amount_approved = sum(request_progress.mapped('max_claim'))
                    res.perc_approved = sum(request_progress.mapped('approved_progress'))
                else:
                    res.amount_approved = 0
                    res.perc_approved = 0
            elif res.request_for == 'retention1':
                request_retention1 = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'retention1'),
                     ('state', '=', 'approved')])
                if len(request_retention1) > 0:
                    res.amount_approved = sum(request_retention1.mapped('max_claim'))
                else:
                    res.amount_approved = 0
            elif res.request_for == 'retention2':
                request_retention2 = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'retention2'),
                     ('state', '=', 'approved')])
                if len(request_retention2) > 0:
                    res.amount_approved = sum(request_retention2.mapped('max_claim'))
                else:
                    res.amount_approved = 0

    @api.depends('request_for', 'contract_amount', 'down_payment', 'retention1', 'retention2', 'requested_progress',
                 'amount_approved')
    def _max_claim_calculation(self):
        for res in self:
            if res.request_for == 'down_payment':
                res.max_claim = res.contract_amount * (res.down_payment / 100) * (res.requested_progress / 100)
                res.gross_amount = 0
                res.dp = 0
                res.reten = 0
                res.approved = 0
            elif res.request_for == 'progress':
                res.max_percen = res.requested_progress + res.perc_approved
                res.gross_amount = (res.max_percen / 100) * res.contract_amount
                res.dp = (res.max_percen / 100) * res.dp_amount
                res.reten = (res.gross_amount * ((res.retention1 / 100) + (res.retention2 / 100)))
                res.max_claim = res.gross_amount - res.dp - res.reten - res.amount_approved
            elif res.request_for == 'retention1':
                res.max_claim = res.contract_amount * (res.retention1 / 100) * (res.requested_progress / 100)
                res.gross_amount = 0
                res.dp = 0
                res.reten = 0
                res.approved = 0
            elif res.request_for == 'retention2':
                res.max_claim = res.contract_amount * (res.retention2 / 100) * (res.requested_progress / 100)
                res.gross_amount = 0
                res.dp = 0
                res.reten = 0
                res.approved = 0

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('claim.request.sequence') or '/'
    #     res = super(CreateClaimRequest, self).create(vals)
    #     return res

    @api.onchange('request_line_ids')
    def onchange_request_line_ids(self):
        if self.request_for == 'progress':
            if self.request_line_ids:
                self.requested_progress = sum(self.request_line_ids.mapped('progress'))
            if self.progressive_bill:
                if len(self.request_line_ids) > 1:
                    raise ValidationError(_("Progressive Bill can only have 1 request line."))

    @api.depends('request_for')
    def _remaining_request_calculation(self):
        for res in self:
            if res.request_for == 'down_payment':
                search_dp = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'down_payment'),
                     ('state', '=', 'approved')])
                approved_dp = sum(search_dp.mapped('approved_progress'))
                res.write({'remaining_request': 100 - approved_dp})
            elif res.request_for == 'retention1':
                search_rent1 = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'retention1'),
                     ('state', '=', 'approved')])
                approved_rent1 = sum(search_rent1.mapped('approved_progress'))
                res.write({'remaining_request': 100 - approved_rent1})
            elif res.request_for == 'retention2':
                search_rent2 = self.env['claim.request.line'].search(
                    [('claim_id', '=', res.progressive_claim_id.id), ('request_for', '=', 'retention2'),
                     ('state', '=', 'approved')])
                approved_rent2 = sum(search_rent2.mapped('approved_progress'))
                res.write({'remaining_request': 100 - approved_rent2})
            elif res.request_for == 'progress':
                res.write({'remaining_request': 0})

    @api.onchange('request_for')
    def onchange_request_for(self):
        for res in self:
            if res.request_for != 'progress':
                res.requested_progress = res.remaining_request

    @api.onchange('requested_progress')
    def onchange_requested_progress(self):
        for res in self:
            if res.request_for == 'down_payment':
                if res.requested_progress > res.remaining_request:
                    raise ValidationError(
                        _("The inputted down payment request exceeds the remaining down payment that can be requested. Please re-set the requested down payment."))
            elif res.request_for == 'retention1':
                if res.requested_progress > res.remaining_request:
                    raise ValidationError(
                        _("The inputted retention 1 request exceeds the remaining retention 1 that can be requested. Please re-set the requested retention 1."))
            elif res.request_for == 'retention2':
                if res.requested_progress > res.remaining_request:
                    raise ValidationError(
                        _("The inputted retention 2 request the remaining retention 2 that can be requested. Please re-set the requested retention 2."))


class RequestLines(models.Model):
    _name = 'const.request.line'
    _description = 'Request Lines'

    request_id = fields.Many2one('claim.request', string="Request ID")
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    work_order = fields.Many2one('project.task', string="Job Order")
    work_order_sub = fields.Many2one('project.task', string="Job Order")
    stage = fields.Many2one('project.stage', string="Stage")
    stage_new = fields.Many2one('project.stage.const', string="Stage")
    worker_assigned_to = fields.Many2one('hr.employee', string="PIC")
    assigned_to = fields.Many2one('res.users', string="PIC")
    completion_date = fields.Datetime(string="Completion Date")
    approved_date = fields.Datetime(string="Approved Date")
    stage_weightage = fields.Float(string="Stage Weightage (%)")
    work_weightage = fields.Float(string="Work Order Weightage (%)")
    work_progress = fields.Float(string="Current WO Progress (%)")
    last_progress = fields.Float(string="Last WO Progress (%)")
    progress = fields.Float(string="Progress (%)", compute="_compute_progress")
    project_id = fields.Many2one(related='request_id.project_id', string='Project')
    progressive_bill = fields.Boolean(related="request_id.progressive_bill")
    progressive_claim_id = fields.Many2one(related="request_id.progressive_claim_id", string="Progressive Claim")
    wo_prog_temp = fields.Float(string="Temporary (%)")
    contract_parent = fields.Many2one(related='request_id.contract_parent', string="Parent Contract")
    contract_parent_po = fields.Many2one(related='request_id.contract_parent_po', string="Parent Contract")
    work_subcon_weightage = fields.Float(string="Job Subcon Weightage")

    @api.onchange('progressive_bill', 'work_order', 'work_order_sub')
    def _onchange_project_id(self):
        self.ensure_one()
        res = {}
        domain_1 = [('project_id', '=', self.project_id.id), ('sale_order', '=', self.contract_parent.id),
                    ('state', '!=', 'draft'), ('claim_request', '=', True), ('is_greater_current_progress', '=', True),
                    ('is_subtask', '=', False)]
        domain_2 = [('project_id', '=', self.project_id.id), ('purchase_subcon', 'in', self.progressive_claim_id.related_contract_po_ids.ids),
                    ('state', '!=', 'draft'), ('claim_request', '=', True), ('is_subcon', '=', True),
                    ('is_greater_current_progress', '=', True), ('is_subtask', '=', False)]
        if self.progressive_bill == False:
            had_claim_request = self.env['claim.request.line'].search([('state', '!=', 'to_approve')]).mapped(
                'request_id')
            domain_3 = [('request_id', 'in', had_claim_request.ids), ('project_id', '=', self.project_id.id)]
            project_task_ids = self.env['const.request.line'].search(domain_3).mapped('work_order')
            ids = []
            for task in project_task_ids:
                if task.progress_task <= task.last_progress:
                    ids.append(task.id)
            domain_1 += [('id', 'not in', ids)]
            res['domain'] = {'work_order': domain_1}
        else:
            had_claim_request = self.env['claim.request.line'].search([('state', '!=', 'to_approve')]).mapped(
                'request_id')
            domain_4 = [('request_id', 'in', had_claim_request.ids), ('project_id', '=', self.project_id.id)]
            project_task_ids = self.env['const.request.line'].search(domain_4).mapped('work_order_sub')
            ids = []
            for task in project_task_ids:
                if task.progress_task <= task.last_progress_subcon:
                    ids.append(task.id)
            domain_2 += [('id', 'not in', ids)]
            res['domain'] = {'work_order_sub': domain_2}
        return res

    @api.model
    def create(self, values):
        list_request_id = self.env['const.request.line'].search(
            [('request_id', '=', values["request_id"]), ('work_order', '=', values["work_order"])])
        if (len(list_request_id) > 0):
            exist_line = list_request_id[0]
            raise ValidationError("The Job Order {} already exists. Please change the Job Order selected.".format(
                exist_line.work_order.name))
        return super(RequestLines, self).create(values)

    @api.depends('request_id.request_line_ids', 'request_id.request_line_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.request_id.request_line_ids:
                no += 1
                l.sr_no = no

    @api.onchange('work_order')
    def onchange_work_order(self):
        if self.work_order:
            self.stage_new = self.work_order.stage_new and self.work_order.stage_new.id or False
            self.worker_assigned_to = self.work_order.worker_assigned_to.id or False
            self.assigned_to = self.work_order.assigned_to and self.work_order.assigned_to.id or False
            self.completion_date = self.work_order.actual_end_date
            self.stage_weightage = self.work_order.stage_weightage
            self.work_progress = self.work_order.progress_task
            self.work_weightage = self.work_order.work_weightage
            self.last_progress = self.work_order.last_progress
            self.wo_prog_temp = self.work_order.wo_prog_temp

    @api.onchange('work_order_sub')
    def onchange_work_order_sub(self):
        if self.work_order_sub:
            self.stage_new = self.work_order_sub.stage_new and self.work_order_sub.stage_new.id or False
            self.worker_assigned_to = self.work_order_sub.worker_assigned_to.id or False
            self.assigned_to = self.work_order_sub.assigned_to and self.work_order_sub.assigned_to.id or False
            self.completion_date = self.work_order_sub.actual_end_date
            self.stage_weightage = self.work_order_sub.stage_weightage
            self.work_subcon_weightage = self.work_order_sub.work_subcon_weightage
            self.work_progress = self.work_order_sub.progress_task
            self.work_weightage = self.work_order_sub.work_weightage
            self.last_progress = self.work_order_sub.last_progress_subcon
            self.wo_prog_temp = self.work_order_sub.wo_prog_temp

    @api.depends('stage_weightage', 'work_weightage', 'work_progress')
    def _compute_progress(self):
        total = 0
        for res in self:
            if res.progressive_bill == False:
                total = ((res.stage_weightage / 100) * (res.work_weightage / 100) * (
                            (res.work_progress - res.last_progress) / 100)) * 100
                res.progress = total
            else:
                total = ((res.work_subcon_weightage / 100) * ((res.work_progress - res.last_progress) / 100)) * 100
                res.progress = total
        return total
