# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, api


class AnalyzeQuotationReport(models.AbstractModel):
    _name = 'report.sh_po_tender_management.report_analyze_quotations'
    _description = "analyze quotations report abstract model"

    @api.model
    def _get_report_values(self, docids, data=None):
        quotation_obj = self.env["purchase.order"]
        partner_quote_dic = {}
        report_model = self.env['ir.actions.report']._get_report_from_name(
            'sh_po_tender_management.report_analyze_quotations')
        tender_obj = self.env['purchase.agreement'].browse(docids)
        partners = self.env['res.partner'].sudo().search([])
        product_price_dic = {}
        quotation_lowest_total = []
        for partner in partners:
            partner_list = []
            domain = [
                ("partner_id", "=", partner.id),
                ("state", "in", ['draft']),
                ('agreement_id', 'in', tender_obj.ids)
            ]
            search_quotations = quotation_obj.search(domain)
            if search_quotations:

                for quotation in search_quotations:
                    quotation_lowest_total.append(quotation.amount_untaxed)
                    for line in quotation.order_line:

                        price_list = product_price_dic.get(
                            line.product_id.id, [])
                        price_list.append(line.price_unit)
                        product_price_dic.update({
                            line.product_id.id: price_list
                        })

                    if quotation.partner_id.id not in partner_list:
                        partner_list.append(quotation.partner_id.id)

            search_partner = self.env['res.partner'].search([
                ('id', 'in', partner_list)
            ], limit=1)

            if search_partner:
                partner_quote_dic.update({search_partner.id: {
                                         "orders": search_quotations, "partner_name": search_partner.name}})
        for k, v in product_price_dic.items():
            lowest_price = min(v)
            product_price_dic.update({
                k: lowest_price
            })
        if len(quotation_lowest_total) > 0:
            quotation_lowest_total = min(quotation_lowest_total)
        else:
            quotation_lowest_total = 0.0
        return {
            'docs': tender_obj,
            'product_price_dic': product_price_dic,
            'quotation_lowest_total': quotation_lowest_total,
            'doc_model': report_model.model,
            'partner_quote_dic': partner_quote_dic
        }
