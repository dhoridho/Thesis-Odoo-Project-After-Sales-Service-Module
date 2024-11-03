# -*- coding: utf-8 -*-
from odoo import api, models, _, release
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import io
import json
import base64
from PIL import Image
import pytesseract
import traceback
import uuid
import requests
import numpy as np
import cv2

from dateutil.parser import parse

import logging

_logger = logging.getLogger(__name__)

DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'


class AiInvoiceDigitizer(models.AbstractModel):
    _name = 'ai.invoice.digitizer'
    _description = 'AI Invoice Digitizer'

    def extract_values_with_ai(self, attachment, invoice=False):
        try:
            invoice = invoice or self.env['account.move'].create({})

            system_prompt = self._ai_system_prompt(invoice_type=invoice.move_type)
            user_prompt = self._ai_user_prompt(attachment)

            response = self._make_iap_request(system_prompt, user_prompt)

            try:
                response_dict = json.loads(response, strict=False)
            except json.decoder.JSONDecodeError:
                fixed_json = self._fix_json_request(response)
                response_dict = json.loads(fixed_json, strict=False)

            partner_id = self._find_partner_from_ai_response(response_dict)

            line_ids = self._find_invoice_lines_from_ai_response(response_dict, invoice.move_type)

            extracted_values = {
                'ref': response_dict.get('invoice_number') or response_dict.get('reference') or response_dict.get('document_number'),
                'invoice_date': response_dict.get('invoice_date') and parse(response_dict.get('invoice_date')).date(),
                'invoice_date_due': response_dict.get('due_date') and parse(response_dict.get('due_date')).date(),
                'payment_reference': response_dict.get('payment_reference'),
                'invoice_line_ids': line_ids,
                'narration': response_dict.get('notes'),
                'partner_id': partner_id and partner_id.id
            }

            invoice.write(extracted_values)

            msg = _("Attachment %s scanned and parsed with AI.", attachment.name)
            invoice.message_post(body=msg)

            return invoice

        except Exception as e:
            _logger.error(f'{e}\n{traceback.format_exc()}')

            if invoice:
                msg = _("There was a problem with digitizing the attachment %s. Please try again or check server logs for more information.", attachment.name)
                invoice.message_post(body=msg)

            return invoice or self.env['account.move']

    def _find_partner_from_ai_response(self, response_dict):
        partner_id = self.env['res.partner'].browse()

        partner_dict = response_dict.get('partner', {})

        name = partner_dict.get('name')
        vat = partner_dict.get('vat_id')
        email = partner_dict.get('email')

        if any([name, vat, email]):
            domain = [('is_company', '=', True), ('id', '!=', self.env.company.id)]

            or_domains = []

            if vat:
                or_domains.append([('vat', '=', vat)])

            if name:
                or_domains.append([('name', '=', name)])

            if email:
                or_domains.append([('email', '=', email)])

            if len(or_domains) == 1:
                domain = expression.AND([domain, or_domains[0]])
            else:
                domain = expression.AND([domain, expression.OR(or_domains)])

            partner_id = self.env['res.partner'].search(domain, limit=1)

        return partner_id

    def _find_invoice_lines_from_ai_response(self, response_dict, move_type):
        line_ids = [(5, 0, 0)]
        for line in response_dict.get('invoice_lines', []):
            try:
                quantity = line.get('quantity') and float(line.get('quantity'))
            except Exception:
                quantity = False

            try:
                price_unit = line.get('price_unit') and float(line.get('price_unit'))
            except Exception:
                price_unit = False

            try:
                discount = line.get('discount') and float(line.get('discount'))
            except Exception:
                discount = False

            try:
                vat_rate = line.get('tax_rate') and float(line.get('tax_rate'))
            except Exception:
                vat_rate = False

            if move_type in ('in_invoice', 'in_refund'):
                type_tax_use = 'purchase'
            else:
                type_tax_use = 'sale'

            tax_id = self.env['account.tax'].search([('type_tax_use', '=', type_tax_use), ('amount', '=', vat_rate), ('amount', '!=', 0.0), ('active', '=', True)], limit=1) if vat_rate else False

            line_ids.append(
                (0, 0, {
                    'name': line.get('product'),
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'tax_ids': tax_id and tax_id.ids
                })
            )
        return line_ids

    @staticmethod
    def _example_response():
        return """        
        {      
             "partner": {
                "name": "String",
                "registry_code": "String",
                "vat_id": "String"
                "email": "String"
             },
             "invoice_number": "String",
             "reference": "String",
             "document_number": "String",
             "invoice_date": "YYYY-MM-DD",
             "due_date": "YYYY-MM-DD",
             "payment_reference": "String",
             "invoice_lines": [
                 {
                     "product": "String",
                     "quantity": Float,
                     "price_unit": Float,
                     "discount": Float,
                     "tax_rate": Float,
                 },
             ],
             "notes": "multiline text"
        } 
        """

    def _parse_attachments_for_ai(self, attachments):
        attachment_data = ''
        for i, attachment in enumerate(attachments, start=1):
            content = base64.b64decode(attachment.with_context(bin_size=False).datas)
            f = io.BytesIO(content)

            if 'pdf' in attachment.mimetype:
                parsed_data = self._parse_pdf_for_ai(f)

                # if pdf parsing returns an empty string, assume the pdf contains scanned images
                # convert pdf to images and scan with ocr
                if parsed_data == '':
                    images = convert_from_bytes(content, dpi=150, fmt='jpeg')

                    for image in images:
                        parsed_data += self._parse_image_for_ai(image)

                attachment_data += f'File {i}: --- {parsed_data} --- '
            elif 'image' in attachment.mimetype:
                attachment_data += f'File {i}: --- {self._parse_image_for_ai(f)} --- '

        return self.clean_string(attachment_data)

    @staticmethod
    def _parse_pdf_for_ai(f):
        parsed_data = ''

        reader = PdfReader(f)
        for page in reader.pages:
            parsed_data += page.extract_text()

        return parsed_data

    def _parse_image_for_ai(self, f):
        try:
            img = Image.open(f)
            dpi = img.info.get('dpi')
        except AttributeError:
            img = f
            dpi = None

        img = self._preprocess_image(img)

        langs = '+'.join(pytesseract.get_languages())

        config = False
        if not dpi:
            config = '--dpi 72'

        text = pytesseract.image_to_string(img, lang=langs, config=config)
        return text

    @staticmethod
    def _preprocess_image(image):
        image_array = np.asarray(image)
        channels = image_array.shape[-1] if image_array.ndim == 3 else 1

        if channels == 3:
            image = cv2.resize(image_array, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            kernel = np.ones((5, 5), np.uint8)
            image = cv2.erode(image, kernel, iterations=1)

        return image

    def _ai_system_prompt(self, invoice_type):
        partner_type, document_type, company_type = False, False, False
        invoice_type_line = ""

        if invoice_type == 'in_invoice':
            partner_type, document_type, company_type = 'vendor', 'bill', 'customer'
        elif invoice_type == 'out_invoice':
            partner_type, document_type, company_type = 'customer', 'invoice', 'vendor'
        elif invoice_type == 'out_refund':
            partner_type, document_type, company_type = 'customer', 'credit note', 'vendor'
        elif invoice_type == 'in_refund':
            partner_type, document_type, company_type = 'vendor', 'credit note', 'customer'

        if all([partner_type, document_type, company_type]):
            invoice_type_line = f"""The document is {partner_type} {document_type} to the {company_type} {self.env.company.name}, 
            you will find out the {partner_type} (partner) and its details. Be careful not to mix vendor and customer."""

        prompt = f"""You are an invoice digitizer.
        I will give you contents extracted with ocr from a document.
        First you will check the contents for errors made by ocr and fix them.
        Then you will extract values from it and fill the json below.
        {invoice_type_line}
        Fill the values in the json with the right data types
        If you find additional useful info, include it in the notes field.
        Do not add any explanations and ``` tags.
        Only provide a valid JSON object adhering to the following structure:
        {self._example_response()}
        """

        return self.clean_string(prompt)

    def _ai_user_prompt(self, attachment):
        text = self._parse_attachments_for_ai(attachment)
        return text

    @staticmethod
    def clean_string(string):
        return " ".join(string.split())

    def _make_iap_request(self, system, prompt):
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = IrConfigParameter.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)

            payload = {
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'prompt': prompt,
                    'conversation_history': [{'role': 'system', 'content': system}],
                    'version': release.version,
                },
                'id': uuid.uuid4().hex,
            }

            req = requests.post(olg_api_endpoint + "/api/olg/1/chat", json=payload, timeout=30)
            req.raise_for_status()
            response = req.json()

            if 'error' in response:
                message = response['error']['data'].get('message')
                raise UserError(message)

            result = response.get('result')

            if result['status'] == 'success':
                return result['content']
            elif result['status'] == 'error_prompt_too_long':
                raise UserError(_("Sorry, the prompt is too long."))
            else:
                raise UserError(_("Sorry, we could not generate a response. Please try again later."))
        except Exception as error:
            raise ValidationError(error)

    def _fix_json_request(self, json_data):
        system = """You are a json fixing tool. You will be given a json string that has some mistakes and causes JSONDecodeError.
        You will fix it and respond with a valid json. Make sure to check for trailing commas, special characters and extra characters among other things.
        Do not add any explanations and ``` tags.
        Only provide a RFC8259 compliant JSON object.
        """
        return self._make_iap_request(system, json_data)
