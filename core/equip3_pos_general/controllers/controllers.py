# -*- coding: utf-8 -*
import json
import os
import jinja2

from datetime import datetime
from passlib.context import CryptContext

import odoo
from odoo import http, _
from .PosWeb import pos_controller 
from odoo.addons.web.controllers import main
from odoo.http import request

crypt_context = CryptContext(schemes=['pbkdf2_sha512', 'plaintext'], deprecated=['plaintext'])
path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../views'))
loader = jinja2.FileSystemLoader(path)
jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

pos_display_template = jinja_env.get_template('pos_display.html')
version_info = odoo.release.version_info[0]

datetime.strptime('2012-01-01', '%Y-%m-%d')


class PosController(pos_controller):

    @http.route(['/point_of_sale/display', '/point_of_sale/display/<string:display_identifier>'], type='http', auth='none')
    def display(self, display_identifier=None):
        cust_js = None
        parent_path = os.path.abspath(__file__ + "/../../")
        with open(parent_path + "/static/src/js/Worker.js") as js:
            cust_js = js.read()
        return pos_display_template.render({
            'title': "Customer Display Screen",
            'breadcrumb': 'POS Client display',
            'cust_js': cust_js,
        })


    @http.route('/pos/update_return_qty', type='json', auth='user', methods=['POST'])
    def my_endpoint(self):
        # Get the data from the request
        data = json.loads(request.httprequest.data)

        # Access the input_data parameter
        line_id = data.get('line_id')
        input_qty = data.get('input_qty')

        # Perform operations with the input data
        # ...
        # for line in self:
        #     result = line.env['pos.order.line'].search([('id', '=', line_id)])
        #     result.write({
        #         'returned_qty' : input_qty,
        #         })

        records = request.env['pos.order.line'].search([('id', '=', line_id)])

        # Update the records
        for record in records:
            existing_returned_qty = record.returned_qty

            record.returned_qty = existing_returned_qty + input_qty
        return "Data received and processed successfully"


class Action(main.Action):

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        if action_id == 'point_of_sale.action_client_pos_menu':
            try:
                request.env.ref(action_id)
            except ValueError:
                action_id = 'equip3_pos_general.action_client_pos_menu'
        return super(Action,self).load(action_id, additional_context=additional_context)