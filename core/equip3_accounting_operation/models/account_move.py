
from odoo import fields, models, api, _ , tools
from datetime import datetime

from odoo.exceptions import UserError, ValidationError
import math

import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _domain_partner_id(self):
        domain = [('company_id','in',[self.env.company.id, False])]
        move_type = self._context.get('default_move_type') or False
        if move_type:
            if move_type in ['out_invoice','out_refund','out_receipt']:
                domain += [('is_customer','=',True)]
            elif move_type in ['in_invoice','in_refund','in_receipt']:
                domain += [('is_vendor','=',True)]
        return domain

    internal_tf_id = fields.Many2one('account.internal.transfer', string="Internal Tf")
    reversal_avail = fields.Boolean(string="Reversal Record", default="False", compute="_compute_reverse_available")
    date_id = fields.Date(string='Due Date')
    is_record_created = fields.Boolean(default=False, compute="_update_subtotal")
    is_merge = fields.Boolean(string="Is Merge", default=False)
    is_merge_to = fields.Boolean(string="Is Merge To", default=False)
    new_invoice_id = fields.Many2one('account.move', string="New Invoice")
    count_merged_invoice = fields.Integer(string="Count Merged Invoice", compute="_compute_count_merged_invoice")
    is_button_update_invisible = fields.Boolean(compute='_compute_is_button_update_invisible')
    partner_id = fields.Many2one('res.partner', domain=_domain_partner_id)
    narration = fields.Html(string='Notes', translate=True, sanitize=False, readonly=False, states={'posted': [('readonly', True)]})
    multi_discount = fields.Char(help="To apply multi discounts, please use the (+) operator (example: 30+20)")
    is_intercompany_transaction = fields.Boolean(string="Intercompany Transaction", default=False)
    apply_manual_currency_exchange = fields.Boolean(string="Apply Manual Currency Exchange")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12,12))
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate", digits=(12,12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)

    @api.onchange("partner_id")
    def _onchange_partner_intercompany(self):
        for rec in self:
            if rec.partner_id:
                if rec.partner_id.is_vendor == False or rec.partner_id.is_customer == False:
                    rec.is_intercompany_transaction = False
            else:
                rec.is_intercompany_transaction = False

    def _validate_intercompany(self):
        for rec in self:
            if rec.is_intercompany_transaction:
                if rec.partner_id:
                    if rec.partner_id.is_vendor == False or rec.partner_id.is_customer == False:
                        raise ValidationError(_("to activate Intercompany Transaction, please set is vendor = true and is customer = true"))
                else:
                    raise ValidationError(_("please select custome/vendor"))

    def create_intercompany_transaction(self):
        for rec in self:
            rec._validate_intercompany()
            move_id = rec
            rec.synchronize(move_id)

    @api.model
    def synchronize(self, moves):
        model_obj = self.env['account.move']        
        company_id = moves.partner_id.related_company_id
        default_company_id = moves.company_id
        fields = False
        value = model_obj.browse([moves.id]).read(fields)[0]
        move_type = 'out_invoice' if moves.move_type == 'in_invoice' else 'in_invoice'
        line_ids = []
        if "create_date" in value:
            del value["create_date"]
        if "write_date" in value:
            del value["write_date"]
        if "line_ids" in value:
            del value["line_ids"]
        if "invoice_line_ids" in value:
            line_ids = value["invoice_line_ids"]
            del value["invoice_line_ids"]
        if "journal_id" in value:
            del value["journal_id"]
        if "move_type" in value:
            del value["move_type"]
        if "is_intercompany_transaction" in value:
            del value["is_intercompany_transaction"]
        if "currency_id" in value:
            del value["currency_id"]
        if "branch_id" in value:
            del value["branch_id"]

        for key, val in value.items():
            if isinstance(val, tuple):
                value.update({key: val[0]})
            
            if key == 'name':
                value.update({key : '/'})
            if key == 'state':
                value.update({key : 'draft'})
            if key == 'state1':
                value.update({key : 'draft'})
            if key == 'state2':
                value.update({key : 'draft'})

        value = self.data_transform('account.move', value, moves, company_id, default_company_id)
        if line_ids:
            move_line_value_id = []
            for line_id in line_ids:
                move_line = self.env['account.move.line'].browse([line_id])
                move_line_value = move_line.read(fields)[0]
                if "create_date" in move_line_value:
                    del move_line_value["create_date"]
                if "write_date" in move_line_value:
                    del move_line_value["write_date"]
                if "move_id" in move_line_value:
                    del move_line_value["move_id"]
                if "exclude_from_invoice_tab" in move_line_value:
                    if move_line_value["exclude_from_invoice_tab"] == True:
                        continue
                for key2, val2 in move_line_value.items():
                    if isinstance(val2, tuple):
                        move_line_value.update({key2: val2[0]})
                move_line_value_id += [(0,0,self.data_transform('account.move.line', move_line_value, move_line, company_id, default_company_id))]
            value['invoice_line_ids'] = move_line_value_id
        branch = self.env['res.branch'].search([('company_id', '=', company_id.id)], limit=1)
        value.update({'branch_id': branch.id})
        move_id = self.env['account.move'].with_company(company_id).with_context(allowed_company_ids=company_id.ids, default_move_type=move_type).create(value)
        move_id.journal_id = move_id._get_default_journal()
        # raise ValidationError("askjdhaskjdhasjkhdjksadh")

    @api.model
    def data_transform(self, obj, data, moves, company_id, default_company_id):
        fields = self.env[obj].fields_get()
        for f in fields:
            if f in data:
                ftype = fields[f]["type"]
                if ftype in ("function", "one2many", "one2one"):
                    del data[f]
                elif ftype == "many2one":
                    if (isinstance(data[f], list)) or (isinstance(data[f], tuple)) and data[f]:
                        fdata = data[f][0]
                    else:
                        fdata = data[f]
                    df = self.relation_transform(fields[f]["relation"], fdata, moves, company_id, default_company_id)
                    data[f] = df
                elif ftype == "many2many":
                    res = map(lambda x: self.relation_transform(fields[f]["relation"], x, moves, company_id, default_company_id), data[f])
                    data[f] = [(6, 0, [x for x in res if x])]
        if "id" in data:
            del data["id"]
        return data

    @api.model
    def relation_transform(self, obj_model, res_id, moves, company_id, default_company_id):
        report = []
        model_obj = self.env[obj_model]
        res = False
        if res_id:
            fields = self.env[obj_model].fields_get()
            domain = []
            if 'company_id' in fields:
                domain = [('company_id', '=', company_id.id)]
            names = model_obj.browse([res_id]).name_get()[0][1]
            if obj_model == "res.country.state":
                name = names.split("(")[0].strip()
                res = self.env[obj_model].with_company(company_id).with_context(allowed_company_ids=company_id.ids)._name_search(name, domain, "=")
                res = [res]
            elif obj_model == "res.country":
                res = self.env[obj_model].with_company(company_id).with_context(allowed_company_ids=company_id.ids)._name_search(names, domain, "=")
                res = [[res[0]]]

            elif obj_model == "account.account":
                if moves.move_id.move_type == 'out_invoice':
                    domain += [('user_type_id.name', '=', 'Income')] 
                else:
                    domain += [('user_type_id.name', '=', 'Expenses')]                
                res = self.env[obj_model].with_company(company_id).with_context(allowed_company_ids=company_id.ids).search(domain, limit=1)
                if res:
                    return res.id
            elif obj_model == "res.partner":
                model_obj = self.env['res.company']
                names = model_obj.browse([default_company_id.id]).name_get()[0][1]
                res = self.env[obj_model].with_company(company_id).with_context(allowed_company_ids=company_id.ids).name_search(names, domain, "=")
            else:
                if obj_model == "res.company":
                    res = company_id
                    return res.id
                else:
                    res = self.env[obj_model].with_company(company_id).with_context(allowed_company_ids=company_id.ids).name_search(names, domain, "=")
            if res:
                result = res[0][0]
                return result    
        return res


    def action_post(self):
        for rec in self:
            if rec.is_intercompany_transaction:
                rec.create_intercompany_transaction()
        result = super(AccountMove, self).action_post()
        return result
                    
    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        # origin_name = self.payment_id.name if self.payment_id else False
        for rec in self:
            if rec.move_type == 'entry':
                if not rec.invoice_date:
                    rec.invoice_date = rec.date
                # if rec.payment_id and (not rec.origin or rec.origin == '/'):
                #     rec.origin = origin_name
                
        return res

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate

    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate

    def round(self, amount):
        self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.currency_id.rounding)
    
    def _convert(self, amount):
        for rec in self:
            if rec.currency_id == rec.company_id.currency_id:
                return rec.currency_id._convert(amount, rec.company_id.currency_id, rec.company_id, rec.date or fields.Date.context_today(rec), round=False)
            else:
                if self.apply_manual_currency_exchange == False:

                    # convert currency using rate ongoing period
                    # first_day_period = rec.account_date.replace(day=1)
                    # end_day_period = first_day_period + relativedelta(months=1, days=-1)
                    # currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', rec.currency_id.id), ('name', '>=', first_day_period), ('name', '<=', end_day_period)], limit=1)
                    
                    # convert currency using last rate
                    currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', rec.currency_id.id), ('name', '<=', rec.account_date)], limit=1)
                    
                    if not currency_rate:
                        raise UserError(_('No currency rate found for the currency %s and the period %s.') % (rec.currency_id.name, rec.account_date))
                    res = amount / currency_rate.rate
                else:
                    res = amount / self.manual_currency_exchange_rate
                
            return self.round(res)
            
    def get_disocunt(self,percentage,amount):
        new_amount = (percentage * amount)/100
        return (amount - new_amount)
 
    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        self.discount_amount = 0
        if self.multi_discount:
            amount = 100
            splited_discounts = self.multi_discount.split("+")
            for disocunt in splited_discounts:
                try:
                    amount = self.get_disocunt(float(disocunt),amount)
                except ValueError:
                    raise ValidationError("Please Enter Valid Multi Discount")
            self.discount_amount = self.discount_amount + (100 - amount)
            to_update = []
            if self.invoice_line_ids:
                for data in self.invoice_line_ids:
                    to_update.append((1,data.id,{'multi_discount':self.multi_discount,'discount_amount':self.discount_amount,'discount_method':self.discount_method}))
                self.invoice_line_ids = to_update
                self._onchange_method_amount()
        else:
            self.discount_amount = 0

    @api.depends('new_invoice_id')
    def _compute_count_merged_invoice(self):
        self.ensure_one()
        count = 0
        old_invoice_ids = self.env['account.move'].search([('new_invoice_id', '=', self.id)])
        for rec in old_invoice_ids:
            count += 1
        self.count_merged_invoice = count

    @api.onchange('analytic_group_ids')
    def _onchange_analytic_group(self):
        for rec in self:
            if rec.invoice_line_ids:
                for line in rec.invoice_line_ids:
                    line.analytic_tag_ids = rec.analytic_group_ids
                for journal_line in rec.line_ids:
                    journal_line.analytic_tag_ids = rec.analytic_group_ids

    @api.onchange('invoice_line_ids.analytic_tag_ids')
    def _rechange_analytic_group(self):
        for rec in self:
            recs = {}
            analytic_ids = []
            rec.analytic_group_ids = [(5, 0, 0)]
            for line in rec.invoice_line_ids:
                for analytic in line.analytic_tag_ids:
                    analytic_name = analytic.name
                    if analytic_name in recs:
                        pass
                    else:
                        recs[analytic_name] = {}
                        analytic_ids.append(analytic.id)
                        rec.analytic_group_ids = [(4, analytic.id)]

    def action_view_merged_invoice(self):
        self.ensure_one()
        if self.move_type == 'out_invoice':
            merged_invoice = []
            old_invoice_ids = self.env['account.move'].search([('new_invoice_id', '=', self.id)])
            if old_invoice_ids:
                for rec in old_invoice_ids:
                    merged_invoice.append(rec.id)
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
            action['name'] = _('Merged Invoice')
            action['domain'] = [('id', 'in', merged_invoice)]

        if self.move_type == 'in_invoice':
            merged_bill = []
            old_bill_ids = self.env['account.move'].search([('new_invoice_id', '=', self.id)])
            if old_bill_ids:
                for rec in old_bill_ids:
                    merged_bill.append(rec.id)
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
            action['name'] = _('Merged Bill')
            action['domain'] = [('id', 'in', merged_bill)]
        action['context'] = {
            'create': False,
            'delete': False,
        }
        return action
    
    @api.model
    def _get_invoice_key_cols_out(self):
        return [
            "partner_id",
            "user_id",
            "move_type",
            "currency_id",
            "journal_id",
            "company_id",
            "bank_partner_id",
            "branch_id",
        ]

    @api.model
    def _get_invoice_key_cols_in(self):
        return [
            "partner_id",
            "move_type",
            "currency_id",
            "journal_id",
            "company_id",
            "bank_partner_id",
            "branch_id",
        ]
    
    @api.model
    def _get_invoice_line_key_cols(self):
        fields = [
            "discount",
            "tax_ids",
            "price_unit",
            "product_id",
            "account_id",
            "analytic_account_id",
            "product_uom_id",
            "analytic_tag_ids",
        ]
        return fields

    @api.model
    def _get_first_invoice_fields(self, invoice):
        return {
            "invoice_origin": invoice.invoice_origin or "",
            "partner_id": invoice.partner_id.id,
            "journal_id": invoice.journal_id.id,
            "user_id": invoice.user_id.id,
            "currency_id": invoice.currency_id.id,
            "company_id": invoice.company_id.id,
            "move_type": invoice.move_type,
            "state": "draft",
            "ref": invoice.ref or "",
            "fiscal_position_id": invoice.fiscal_position_id.id,
            "invoice_payment_term_id": False,
            "invoice_line_ids": {},
            "bank_partner_id": False,
            "branch_id": invoice.branch_id.id,
            "active_manual_currency_rate": invoice.active_manual_currency_rate,
        }

    def merge_invoices(self):
        for invoice_line in self:
            ids = invoice_line.env.context.get("active_ids", [])
            if len(ids) < 2:
                raise ValidationError(_("Please select multiple invoices to merge in the list " "view."))
            invoices = invoice_line.browse(ids)
            not_draft = invoices.filtered(lambda x: x.state != "draft")
            partners = []
            branches = []
            currencies = []
            for rec in invoices:
                if rec.partner_id.id not in partners:
                    partners.append(rec.partner_id.id)
                if rec.branch_id.id not in branches:
                    branches.append(rec.branch_id.id)
                if rec.currency_id.id not in currencies:
                    currencies.append(rec.currency_id.id)
            if not_draft or len(partners) > 1 or len(branches) > 1 or len(currencies) > 1:
                raise ValidationError(_('The invoice must have the same customer name, branch, currency type, and be in draft status'))
        
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = br[field]
                if isinstance(field_val, models.BaseModel):
                    if br._fields.get(field).type in ("one2many", "many2many"):
                        field_val = tuple([(6, 0, tuple(field_val.ids))])
                    else:
                        field_val = field_val.id
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)

        new_invoices = {} 
        seen_origins = {}
        seen_client_refs = {}

        for account_invoice in invoices:
            invoice_key = []
            if account_invoice.move_type in ("in_invoice"):
                invoice_key = make_key(account_invoice, self._get_invoice_key_cols_in())
            elif account_invoice.move_type in ("out_invoice"):
                invoice_key = make_key(account_invoice, self._get_invoice_key_cols_out())
            else:
                raise ValidationError(_('select only Invoices or Bills'))
            new_invoice = new_invoices.setdefault(invoice_key, ({}, []))
            origins = seen_origins.setdefault(invoice_key, set())
            client_refs = seen_client_refs.setdefault(invoice_key, set())
            new_invoice[1].append(account_invoice.id)
            invoice_infos = new_invoice[0]

            if not invoice_infos:
                invoice_infos.update(self._get_first_invoice_fields(account_invoice))
                origins.add(account_invoice.invoice_origin)
                client_refs.add(account_invoice.ref)
            else:
                if (
                    account_invoice.invoice_origin
                    and account_invoice.invoice_origin not in origins
                ):
                    invoice_infos["invoice_origin"] = (
                        (invoice_infos["invoice_origin"] or "")
                        + " "
                        + account_invoice.invoice_origin
                    )
                    origins.add(account_invoice.invoice_origin)
                if account_invoice.ref and account_invoice.ref not in client_refs:
                    invoice_infos["ref"] = (
                        (invoice_infos["ref"] or "") + " " + account_invoice.ref
                    )
                    client_refs.add(account_invoice.ref)

            for invoice_line in account_invoice.invoice_line_ids:
                line_key = make_key(invoice_line, self._get_invoice_line_key_cols())
                o_line = invoice_infos["invoice_line_ids"].setdefault(line_key, {})
                # append a new "standalone" line
                o_line["quantity"] = invoice_line.quantity
        allinvoices = []
        allnewinvoices = []
        invoices_info = {}
        old_invoices = self.browse()
        for _invoice_key, (invoice_data, old_ids) in new_invoices.items():
            # skip merges with only one invoice
            if len(old_ids) < 2:
                allinvoices += old_ids or []
                continue
            # cleanup invoice line data
            for key, value in invoice_data["invoice_line_ids"].items():
                value.update(dict(key))
            invoice_data["invoice_line_ids"] = [(0, 0, value) for value in invoice_data["invoice_line_ids"].values()]
            invoice_data["invoice_date"] = fields.Date.today()
            invoice_data["attn"] = ''
            invoice_data["analytic_group_ids"] = [(5,0,0)]
            invoice_data["discount_type"] = 'global'
            invoice_data["is_merge"] = True
            newinvoice = self.create(invoice_data)
            newinvoice.write({"invoice_date_due": False})
            invoices_info.update({newinvoice.id: old_ids})
            allinvoices.append(newinvoice.id)
            allnewinvoices.append(newinvoice)
            # cancel old invoices
            old_invoices = self.browse(old_ids)
            old_invoices.write({"is_merge_to": True, "new_invoice_id": newinvoice.id,})
            old_invoices.button_cancel()
        aw_obj = self.env["ir.actions.act_window"]
        xid = {
                  "out_invoice": "account.action_move_out_invoice_type",
                  "in_invoice": "account.action_move_in_invoice_type",
              }[fields.first(invoices).move_type]
        res = aw_obj._for_xml_id(xid)
        res["domain"] = [("id", "in", ids + list(invoices_info.keys()))]
        return res
    
    def _update_subtotal(self):
        res_config = self.company_id.tax_discount_policy or False
        res_config_sale_account_id = self.company_id.sale_account_id.id or False
        if self.is_record_created == False:
            for record in self:
                discount_amt1 = 0
                total_discount_with_tax = 0 
                for data in record.invoice_line_ids:
                    record.is_record_created = True

    @api.depends('amount_tax')
    def _compute_amount2(self):
        for move in self:
            move.amount_tax2 = move.amount_tax    

    @api.depends('invoice_payment_term_id','check_date','check_month')
    def _compute_is_button_update_invisible(self):
        today = fields.Date.today()
        for record in self:
            payment_term_id = record.invoice_payment_term_id
            if(payment_term_id.interest_type == 'daily'):
                if str(record.check_date) == str(today):
                    invisible = True
                else:
                    invisible = False
            else:
                if int(record.check_month) == today.month:
                    invisible = True
                else:
                    invisible = False
            record.is_button_update_invisible = invisible

    @api.depends('ref')
    def _compute_reverse_available(self):
        for record in self:
            name_auto_reversal = 'Reversal of:' + ' ' + self.name +', Scheduled'
            domain_auto_reversal = [('ref','like', name_auto_reversal)]
            auto_reversal_record = self.env['account.move'].search(domain_auto_reversal)
            if auto_reversal_record:
                self.reversal_avail = True
            else:
                self.reversal_avail = False
            
    @api.model
    def partner_domain(self):
        company = self.env.company.id
        return [('company_id', '=', company)]

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        # domain.extend([('company_id', '=', self.env.company.id)])
        return super(AccountMove, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        # domain.extend([('company_id', '=', self.env.company.id)])
        return super(AccountMove, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def refresh_discount(self):
        self.ensure_one()

    @api.onchange('discount_type')
    def _onchange_disc_method(self):
        for rec in self:
            if rec.discount_type == 'global':
                if not rec.discount_method:
                    rec.discount_method = 'fix'

    def button_add_interest(self):
        result=super(AccountMove,self).button_add_interest()
        interest_lines = self.line_ids.filtered(lambda line: line.is_interest_line)
        receivable_line = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'receivable')
        payable_line = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'payable')
        discount_line = self.line_ids.filtered(lambda line: line.is_discount_line)
        if not self.interest:
            if interest_lines:
                self.line_ids = [(2,interest.id)for interest in interest_lines]
        else:
            if interest_lines:
                interest_lines.filtered(lambda i : i.debit > 0).debit = self.interest
                interest_lines.filtered(lambda i : i.credit > 0).credit = self.interest
            else:
                if self.move_type == 'out_invoice':
                    account_id = self.partner_id.interest_customer_account_receivable.id
                    key = 'debit'
                    this_line = receivable_line
                else:
                    account_id = self.partner_id.interest_vendor_account_payable.id
                    key = 'credit'
                    this_line = payable_line
                self.line_ids= [(0,0,{'account_id' : account_id,
                                      'name': "Account Receivable Interest" + str(self.name) + datetime.today().strftime('%Y/%m/%d'),
                                      key: self.interest,
                                      'is_interest_line' : True}),
                                (1, this_line.id, {key: this_line[key] - self.interest})]

    def button_reverse_journal(self):
        name_reversal = 'Reversal of:' + ' ' + self.name
        name_auto_reversal = 'Reversal of:' + ' ' + self.name +', Scheduled'
        domain_reversal = [('ref','like', name_reversal)]
        domain_auto_reversal = [('ref','like', name_auto_reversal)]
        reversal_record = self.env['account.move'].search(domain_reversal)
        auto_reversal_record = self.env['account.move'].search(domain_auto_reversal)
        if auto_reversal_record:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'context': {'create': False},
                'view_mode': 'form',
                'res_id': auto_reversal_record.id,
            }
        else:
            action = {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'context': {'create': False},
                'view_mode': 'form',
                'res_id': reversal_record.id,
            }
        return action

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        lines_vals_list = super(AccountMove, self)._stock_account_prepare_anglo_saxon_out_lines_vals()
        for line_vals_list in lines_vals_list:
            if not line_vals_list.get('price_subtotal'):
                line_vals_list['price_subtotal'] = line_vals_list['debit'] > 0 and line_vals_list['debit'] or -line_vals_list['credit'] 
        
        return lines_vals_list

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    date_id = fields.Date(string='Due Date')
    is_discount_line = fields.Boolean()
    is_interest_line = fields.Boolean()
    is_analytic_tags = fields.Boolean("Is Analytic Group", compute="compute_group_analytic", default=lambda self: bool(self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False)))
    total_qty_price_unit = fields.Monetary(string='total_qty_price_unit', store=True, readonly=True, currency_field='currency_id', compute="_get_total_qty_price_unit")
    multi_discount = fields.Char()
    is_intercompany_transaction = fields.Boolean(string="Intercompany Transaction", related='move_id.is_intercompany_transaction')
    
    def get_disocunt(self,percentage,amount):
        new_amount = (percentage * amount)/100
        return (amount - new_amount)
 
    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        if self.multi_discount:
            amount = 100
            splited_discounts = self.multi_discount.split("+")
            for disocunt in splited_discounts:
                try:
                    amount = self.get_disocunt(float(disocunt),amount)
                except ValueError:
                    raise ValidationError("Please Enter Valid Multi Discount")
            self.discount_amount = 100 - amount
        else:
            self.discount_amount = 0

    @api.depends('quantity', 'price_unit')
    def _get_total_qty_price_unit(self):
        for rec in self:
            if (rec.quantity and rec.price_unit) and rec.quantity != 0 and rec.price_unit != 0:
                rec.total_qty_price_unit = rec.quantity * rec.price_unit
            else:
                rec.total_qty_price_unit = 0

    def compute_group_analytic(self):
        for rec in self:
            rec.is_analytic_tags = bool(
                self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False))

    """ To be inherited in purchase down payment """
    def _get_discount_value(self, force_final_discount=None):
        move = self.move_id
        if not move:
            return 0.0
        final_discount = 0.0
        if force_final_discount is None:
            if move.discount_method == 'per':
                final_discount = (move.discount_amount * self.price_subtotal) / 100.0
            elif move.discount_method == 'fix':
                final_discount =  move.discount_amount
        return self.price_subtotal - final_discount