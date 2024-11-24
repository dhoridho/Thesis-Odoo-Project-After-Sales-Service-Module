from odoo import models, fields, api, _
from odoo.exceptions import Warning
from reportlab.graphics import barcode
from base64 import b64encode


class BarcodeProductLines(models.TransientModel):
    _inherit = "barcode.product.lines"

    qty = fields.Integer(
        'Barcode Labels Quantity',
        default=1,
        required=True
    )

    is_multi_barcode = fields.Boolean(related="product_id.multi_barcode")


class ReportBarcodeLabels(models.AbstractModel):
    _inherit = 'report.dynamic_barcode_labels.report_barcode_labels'

    def _get_barcode_string(self, product, data):
        # barcode_value = product[str(data['form']['barcode_field'])]
        barcode_value = product
        # print('ba',barcode_value)
        # barcode_value = product
        barcode_str = barcode.createBarcodeDrawing(
            data['form']['barcode_type'],
            value=barcode_value,
            format='png',
            width=int(data['form']['barcode_height']),
            height=int(data['form']['barcode_width']),
            humanReadable=data['form']['humanreadable']
        )
        encoded_string = b64encode(barcode_str.asString('png'))
        barcode_str = "<img style='width:" + str(data['form']['display_width']) + "px;height:" + str(data['form']['display_height']) + "px'src='data:image/png;base64,{0}'>".format(encoded_string.decode("utf-8"))
        return barcode_str or ''

class BarcodeLabels(models.TransientModel):
    _inherit = "barcode.labels"

    def print_report(self):
        if not self.env.user.has_group('dynamic_barcode_labels.group_barcode_labels'):
            raise Warning(_("You have not enough rights to access this "
                            "document.\n Please contact administrator to access "
                            "this document."))
        if not self.product_get_ids:
            raise Warning(_(""" There is no product lines to print."""))
        config_rec = self.env['barcode.configuration'].search([], limit=1)
        if not config_rec:
            raise Warning(_(" Please configure barcode data from "
                            "configuration menu"))
        datas = {
            'ids': [x.product_id.id for x in self.product_get_ids],
            'model': 'product.product',
            'form': {
                'label_width': config_rec.label_width or 50,
                'label_height': config_rec.label_height or 50,
                'margin_top': config_rec.margin_top or 1,
                'margin_bottom': config_rec.margin_bottom or 1,
                'margin_left': config_rec.margin_left or 1,
                'margin_right': config_rec.margin_right or 1,
                'dpi': config_rec.dpi or 90,
                'header_spacing': config_rec.header_spacing or 1,
                'barcode_height': config_rec.barcode_height or 300,
                'barcode_width': config_rec.barcode_width or 1500,
                'barcode_type': config_rec.barcode_type or 'EAN13',
                'barcode_field': config_rec.barcode_field or '',
                'display_width': config_rec.display_width,
                'display_height': config_rec.display_height,
                'humanreadable': config_rec.humanreadable,
                'product_name': config_rec.product_name,
                'product_variant': config_rec.product_variant,
                'price_display': config_rec.price_display,
                'lot': config_rec.lot,
                'product_code': config_rec.product_code or '',
                'barcode': config_rec.barcode,
                'currency_position': config_rec.currency_position or 'after',
                'currency': config_rec.currency and config_rec.currency.id or '',
                'symbol': config_rec.currency and config_rec.currency.symbol or '',
                'product_ids': [{
                    'product_id': line.product_id.id,
                    'lot_id': line.lot_id and line.lot_id.id or False,
                    'lot_number': line.lot_id and line.lot_id.name or False,
                    'qty': line.qty,
                } for line in self.product_get_ids]
            }
        }
        for line in self.product_get_ids:
            if line.product_id.multi_barcode == True:
                # if line.qty > 1:
                line.product_id.barcode = ''
                for multi_bc in line.product_id.barcode_line_ids:
                # for i in range(line.qty):
                    # print('i',i)
                    line.product_id.barcode = line.product_id.barcode_line_vals
                    # line.product_id.barcode = multi_bc.name
        # browse_pro = self.env['product.product'].browse([x.product_id.id for x in self.product_get_ids])
        # for product in browse_pro:
        #     barcode_value = product[config_rec.barcode_field]
        #     if not barcode_value:
        #         raise Warning(_('Please define barcode for %s!' % (product['name'])))
        #     try:
        #         barcode.createBarcodeDrawing(
        #             config_rec.barcode_type,
        #             value=barcode_value,
        #             format='png',
        #             width=int(config_rec.barcode_height),
        #             height=int(config_rec.barcode_width),
        #             humanReadable=config_rec.humanreadable or False
        #         )
        #     except:
        #         raise Warning('Select valid barcode type according barcode field value or check value in field!')
        for line in self.product_get_ids:
            barcode_value = False
            if line.product_id.multi_barcode:
                barcode_value = line.barcode.name
            else:
                barcode_value = line.product_id[config_rec.barcode_field]

            if not barcode_value:
                raise Warning(_('Please define barcode for %s!' % (line.product_id['name'])))

            try:
                barcode.createBarcodeDrawing(
                    config_rec.barcode_type,
                    value=barcode_value,
                    format='png',
                    width=int(config_rec.barcode_height),
                    height=int(config_rec.barcode_width),
                    humanReadable=config_rec.humanreadable or False
                )
            except:
                raise Warning('Select valid barcode type according barcode field value or check value in field!')

        self.sudo()._create_paper_format(datas['form'])
        barcode_list = []
        for line in self.product_get_ids.mapped("product_id"):
            for i in self.product_get_ids:
                barcode_list.extend(((i.product_id.id,i.barcode.name), )* i.qty)
            line.barcode_labels_line_data = barcode_list
        return self.env.ref('dynamic_barcode_labels.barcodelabels').report_action([], data=datas)

                # else:
                #     line.product_id.barcode = line.product_id.barcode_line_vals
                # print(zzzz)
        #
        # browse_pro = self.env['product.product'].browse([x.product_id.id for x in self.product_get_ids])
        # for product in browse_pro:
        #     barcode_value = product[config_rec.barcode_field]
        #     if not barcode_value:
        #         raise Warning(_('Please define barcode for %s!' % (product['name'])))
        #     try:
        #         barcode.createBarcodeDrawing(
        #             config_rec.barcode_type,
        #             value=barcode_value,
        #             format='png',
        #             width=int(config_rec.barcode_height),
        #             height=int(config_rec.barcode_width),
        #             humanReadable=config_rec.humanreadable or False
        #         )
        #     except:
        #         raise Warning('Select valid barcode type according barcode field value or check value in field!')

        # self.sudo()._create_paper_format(datas['form'])
        # return self.env.ref('dynamic_barcode_labels.barcodelabels').report_action([], data=datas)
