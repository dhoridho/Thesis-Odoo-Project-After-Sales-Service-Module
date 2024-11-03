import io
import base64
import xlsxwriter
from odoo import models, _

MONTH_NAMES = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december'
]


def format_float(value, rounding):
    return ("{:." + str(rounding) + "f}").format(value)


class BudgetPlanningBlock(models.Model):
    _inherit = 'agriculture.budget.planning.block'

    def action_print_pdf(self):
        return self.env.ref('equip3_agri_reports.action_print_agriculture_budget_planning_block_report').report_action(self)

    def action_print_xlsx(self):
        file_name = 'Budget Planning Report.xlsx'

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        
        RNG = xlsxwriter.utility.xl_range

        title_format = workbook.add_format({
            'bold': 1,
            'font_size': 15,
        })

        header_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
        })

        bold = workbook.add_format({
            'bold': 1
        })

        bordered = workbook.add_format({
            'border': 1
        })

        bold_bordered = workbook.add_format({
            'bold': 1,
            'border': 1
        })

        row = 1
        worksheet.write(row, 0, '%s: %s' % (self.env.company.display_name, _('Budget Planning Report')), title_format)

        width = [2 for i in range(18)]
        for record in self:
            row += 2
            worksheet.write(row, 0, 'Estate', bold)
            worksheet.write(row, 1, ': %s' % record.estate_id.display_name, bold)
            worksheet.write(row, 7, 'Company', bold)
            worksheet.write(row, 8, ': %s' % record.company_id.display_name, bold)

            row += 1
            worksheet.write(row, 0, 'Division', bold)
            worksheet.write(row, 1, ': %s' % record.division_id.display_name, bold)
            worksheet.write(row, 7, 'Branch', bold)
            worksheet.write(row, 8, ': %s' % record.branch_id.display_name, bold)

            row += 1
            worksheet.write(row, 0, 'Year', bold)
            worksheet.write(row, 1, ': %s' % record.year, bold)
            worksheet.write(row, 7, 'Created On', bold)
            worksheet.write(row, 8, ': %s' % record.create_date.strftime('%m/%d/%Y'), bold)

            row += 1
            worksheet.write(row, 0, 'Responsible', bold)
            worksheet.write(row, 1, ': %s' % record.user_id.display_name, bold)
            worksheet.write(row, 7, 'Created By', bold)
            worksheet.write(row, 8, ': %s' % record.create_uid.display_name, bold)

            row += 2
            for i, head in enumerate(['BLOCK', 'TT', 'HA', 'PKK', 'SPH'] + [m.upper() for m in MONTH_NAMES] + ['TOTAL']):
                worksheet.write(row, i, head, header_format)
                width[i] = max([width[i], len(str(head)) + 2])

            row += 1
            for month in record.month_ids:
                for i, key in enumerate(['block_id', 'tt', 'ha', 'pkk', 'sph'] + ['val_' + m[:3] for m in MONTH_NAMES] + ['total']):
                    if key == 'block_id':
                        value = month.block_id.display_name
                    elif key == 'tt':
                        value = month.tt and str(month.tt) or ''
                    elif key in ['ha', 'pkk', 'sph']:
                        value = format_float(month[key], 2)
                    else:
                        value = '%s %s' % (month.currency_id.symbol, format_float(month[key], 2))
                    worksheet.write(row, i, value, key != 'total' and bordered or bold_bordered)
                    width[i] = max([width[i], len(str(value)) + 2])
                row += 1

            currency_id = record.company_id.currency_id

            worksheet.merge_range(RNG(row, 0, row, 1), 'Total', bold_bordered)
            for i, key in enumerate(['ha', 'pkk', 'sph'] + ['val_' + m[:3] for m in MONTH_NAMES] + ['total']):
                if key in ['ha', 'pkk', 'sph']:
                    value = format_float(sum(record.month_ids.mapped(key)), 2)
                else:
                    value = '%s %s' % (currency_id.symbol, format_float(sum(record.month_ids.mapped(key)), 2))
                worksheet.write(row, i + 2, value, bold_bordered)
                width[i + 2] = max([width[i + 2], len(str(value)) + 2])

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment_id.id,
            'target': 'self'
        }