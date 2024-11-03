from odoo.http import request
from odoo import http
import json
from datetime import date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from werkzeug.utils import redirect


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return super().default(obj)


class AccountController(http.Controller):

    @http.route(['/manual_reconcile', '/entries'], auth='user')
    def dock(self, **kw):
        # Check if the user has the 'account.group_account_user' group
        if request.env.user.has_group('account.group_account_user') or request.env.user.has_group(
                'account.group_account_invoice'):
            journal = request.env['account.move.line'].search(
                [('manual_reconciled', '=', "match")])
            # for j in journal:
            #     j.manual_reconciled = 'not_match'

            # User has the group, render the desired template
            return request.render('equip3_recon_wizard.reconcile_template')
        else:
            # User does not have the group, redirect to '/not_auth'
            return redirect('/')

    @http.route('/reconcile/company', type='http', auth='user', csrf=False, cors='*')
    def get_company(self):
        companies = request.env['res.company'].search([])

        company_data = []

        if companies:
            for company in companies:
                company_data.append({
                    'id': company.id,
                    'name': company.name,
                    'currency': company.currency_id.symbol

                })
            result = {
                'status': 'success',
                'data': company_data
            }

            return json.dumps(result)
        else:
            return json.dumps({
                'status': 'no company found',

            })

    @http.route('/reconcile/reconciled_data', type='http', auth='user', csrf=False, cors='*')
    def get_reconciled_date(self):
        data = request.env['manual.reconcile.report'].search([])

        reconcile_data = []

        if data:
            for entry in data:
                reconcile_data.append({
                    'report_id': entry.id,
                    'company_id': entry.company_id.name,
                    'currency': entry.company_id.currency_id.symbol,
                    'account_id': entry.account_id.name,
                    'ending_date': entry.ending_date,
                    'ending_balance': entry.ending_balance,
                    'starting_balance': entry.starting_balance,
                    'difference': entry.difference,
                    'state': entry.state,
                    'account_move_line_ids': entry.account_move_line_ids.ids,
                })
            result = {
                'status': 'success',
                'data': reconcile_data
            }

            return json.dumps(result)
        else:
            return json.dumps({
                'status': 'no data found',

            })

    @http.route('/reconcile/reconciled_data/<int:object_id>', type='http', auth='user', csrf=False, cors='*')
    def resume_reconciled_date(self, object_id):
        data = request.env['manual.reconcile.report'].search([('id', '=', object_id)])

        reconcile_data = []

        if data:
            for entry in data:
                reconcile_data.append({
                    'report_id': entry.id,
                    'company_id': entry.company_id.id,
                    'currency': entry.company_id.currency_id.symbol,
                    'account_id': entry.account_id.id,
                    'ending_date': entry.ending_date,
                    'ending_balance': entry.ending_balance,
                    'difference': entry.difference,
                    'starting_balance': entry.starting_balance,
                    'state': entry.state,
                    'account_move_line_ids': entry.account_move_line_ids.ids,
                })
            result = {
                'status': 'success',
                'data': reconcile_data
            }

            return json.dumps(result)
        else:
            return json.dumps({
                'status': 'no data found',

            })

    @http.route('/reconcile/accounts/<int:company_id>', type='http', auth='user', csrf=False, cors='*')
    def get_accounts(self, company_id):
        Account = request.env['account.account']
        account_type_bank_and_cash = request.env.ref('account.data_account_type_liquidity').id
        accounts = Account.search([('company_id', '=', company_id),('user_type_id','=',account_type_bank_and_cash)])
        account_data = []
        # print(accounts)

        if accounts:
            for account in accounts:

                account_data.append({
                    'id': account.id,
                    'name': account.code + ' ' + account.name,
                    'beginning_balance': account.beginning_balance,
                    'last_statement_ending_date': account.last_statement_ending_date,
                })
            result = {
                'status': 'success',

                'data': account_data
            }

            return json.dumps(result)
        else:
            return json.dumps({
                'status': 'no account found',

            })

    @http.route('/reconcile/invoices/<int:company_id>/<int:account_id>', type='http', auth='user', csrf=False,
                cors='*')
    def get_invoices_for_account(self, company_id, account_id, **kwargs):
        date_str = kwargs['date']
        # account_id=kwargs

        Account = request.env['account.account']
        accounts = Account.search([('company_id', '=', company_id) and ('id','=',account_id)])
        account_name = accounts.code +" "+accounts.name

        # Convert to datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        # Format to 'DD-MM-YYYY'
        # formatted_date = date_obj.strftime('%m/%d/%Y')
        formatted_date = date_obj.strftime('%Y-%m-%d')
        print(formatted_date)
        # formatted_date = date_obj.strftime('%m/%d/%Y')

        global beginning_balance
        query = f"""
        SELECT
            aml.id AS invoice_id,
            am.state AS status,
            aml.ref AS ref,
            aml.account_id AS account_id,
            aml.manual_reconciled as manual_reconcile,
            aa.code || ' ' || aa.name AS account_name,
            am.date AS invoice_date,
            am.company_id AS company_id,
            rc.name AS company_name,
            res_partner.name AS partner_name,
            SUM(aml.credit) AS credit,
            SUM(aml.debit) AS debit,
            aj.name AS invoice_type
        FROM
            account_move AS am
        JOIN
            account_move_line AS aml ON am.id = aml.move_id
        JOIN
            account_account AS aa ON aml.account_id = aa.id
        LEFT JOIN
            res_partner ON am.partner_id = res_partner.id
        JOIN
            account_journal AS aj ON am.journal_id = aj.id
        JOIN
            res_company AS rc ON am.company_id = rc.id
        WHERE
            am.state = 'posted'
            AND aa.id = {account_id}
            AND am.date IS NOT NULL
            AND aml.manual_reconciled = 'not_match'
            AND am.company_id = {company_id}
            AND am.date <= '{formatted_date}'
        GROUP BY
            aml.id, am.company_id, aml.ref, aml.manual_reconciled, aml.account_id, aa.code, aa.name, am.date, rc.name, res_partner.name, aj.name, am.state;
            
	"""
        request._cr.execute(query)
        invoice_data = request._cr.dictfetchall()

        for entry in invoice_data:
            if isinstance(entry['invoice_type'], dict):
                entry['invoice_type'] = list(entry['invoice_type'].values())[0]

            if isinstance(entry['account_name'], str):
                entry['account_name']= account_name

        result = {
            'status': 'success',
            'data': invoice_data
        }

        return json.dumps(result, cls=CustomJSONEncoder)

    @http.route('/reconcile/invoices/save/<int:company_id>', type='json', auth='user', csrf=False, cors='*',
                methods=['POST', 'GET', 'OPTIONS'])
    def get_reconciled_data(self, company_id, **kwargs):
        try:
            json_data = json.loads(request.httprequest.data)
            if json_data:
                account_id = json_data['account_id']
                item_ids = json_data['reconciled_entries']
                ending_date = json_data['ending_date']
                bal = json_data['ending_balance']
                startbal = json_data['starting_balance']
                diffbal = json_data['difference']
                state = json_data['state']
                report_id = json_data['report_id']
                account = request.env['account.account'].sudo().search(
                    [('company_id', '=', company_id), ('id', '=', int(account_id))])
                if account:
                    account[0].beginning_balance = float(bal)
                    account[0].last_statement_ending_date = ending_date
                int_array = [int(item) for item in item_ids]
                if state == 'completed':
                    for journal_id in int_array:
                        journal = request.env['account.move.line'].sudo().search(
                            [('company_id', '=', company_id), ('id', '=', journal_id)])
                        journal[0].manual_reconciled = 'match'

                values = {
                    'company_id': company_id,
                    'account_id': account_id,
                    'ending_date': ending_date,
                    'starting_balance': startbal,
                    'difference': diffbal,
                    'state': state,
                    'ending_balance': float(bal),  # Example balance
                    'account_move_line_ids': [(6, 0, int_array)],
                }
                if report_id:
                    report = request.env['manual.reconcile.report'].search([('id', '=', report_id)])
                    report.account_move_line_ids = False
                    report.write(values)
                elif state == 'pending' and not report_id:
                    new_report = request.env['manual.reconcile.report'].create(values)
                elif state == 'completed' and not report_id:
                    new_report = request.env['manual.reconcile.report'].create(values)
            return {
                'status': 'Success'
            }
        except Exception as e:
            print(e)
            return {'status': 'Failed', 'message': f'Error: Invalid data!!! {str(e)}'}
