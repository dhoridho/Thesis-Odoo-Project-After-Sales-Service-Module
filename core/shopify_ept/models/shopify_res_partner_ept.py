# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api

_logger = logging.getLogger("Shopify Logs")


class ShopifyResPartnerEpt(models.Model):
    _name = "shopify.res.partner.ept"
    _description = "Shopify Res Partner"

    partner_id = fields.Many2one("res.partner", ondelete="cascade")
    shopify_instance_id = fields.Many2one("shopify.instance.ept", "Instances")
    shopify_customer_id = fields.Char()

    def shopify_create_contact_partner(self, vals, instance, queue_line, log_book):
        """
        This method is used to create a contact type customer.
        @author: Maulik Barad on Date 09-Sep-2020.
        """
        partner_obj = self.env["res.partner"]
        common_log_line_obj = self.env["common.log.lines.ept"]

        shopify_instance_id = instance.id
        shopify_customer_id = vals.get("id", False)
        first_name = vals.get("first_name", "")
        last_name = vals.get("last_name", "")
        email = vals.get("email", "")

        if not first_name and not last_name and not email:
            message = "First name, Last name and Email are not found in customer data."
            model_id = common_log_line_obj.get_model_id("res.partner")
            common_log_line_obj.shopify_create_customer_log_line(message, model_id, queue_line, log_book)
            return False

        name = ""
        if first_name:
            name = "%s" % first_name.strip()
        if last_name:
            name += " %s" % last_name.strip() if name else "%s" % last_name
        if not name and email:
            name = email

        partner = self.search_shopify_partner(shopify_customer_id, shopify_instance_id)

        if partner:
            if not partner.email:
                partner.write({"email": email})
            return partner

        shopify_partner_values = {"shopify_customer_id": shopify_customer_id,
                                  "shopify_instance_id": shopify_instance_id}
        if email:
            partner = partner_obj.search_partner_by_email(email)

            if partner:
                partner.write({"is_shopify_customer": True})
                shopify_partner_values.update({"partner_id": partner.id})
                self.create(shopify_partner_values)
                return partner

        partner_vals = self.shopify_prepare_partner_vals(vals.get("default_address", {}))

        partner_vals.update({
            "name": name.strip(),
            "email": email,
            "customer_rank": 1,
            "is_shopify_customer": True,
            "type": "contact",
        })
        partner = partner_obj.create(partner_vals)

        shopify_partner_values.update({"partner_id": partner.id})
        self.create(shopify_partner_values)

        return partner

    def search_shopify_partner(self, shopify_customer_id, shopify_instance_id):
        """ This method is used to search the shopify partner.
            :param shopify_customer_id: Id of shopify customer which receive from customer response.
            @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 27 October 2020 .
            Task_id: 167537
        """
        partner = False
        shopify_partner = self.search([("shopify_customer_id", "=", shopify_customer_id),
                                       ("shopify_instance_id", "=", shopify_instance_id)], limit=1)
        if shopify_partner:
            partner = shopify_partner.partner_id
            return partner

        return partner

    @api.model
    def shopify_create_or_update_address(self, shopify_customer_data, partner_email, parent_partner,
                                         partner_type="contact"):
        """
        Creates or updates existing partner from Shopify customer's data.
        @author: Maulik Barad on Date 09-Sep-2020.
        """
        partner_obj = self.env["res.partner"]

        first_name = shopify_customer_data.get("first_name")
        last_name = shopify_customer_data.get("last_name")

        if not first_name and not last_name:
            return False

        company_name = shopify_customer_data.get("company")
        partner_vals = self.shopify_prepare_partner_vals(shopify_customer_data)
        address_key_list = ["name", "street", "street2", "city", "zip", "phone", "state_id", "country_id"]

        if company_name:
            address_key_list.append("company_name")
            partner_vals.update({"company_name": company_name})

        partner = partner_obj._find_partner_ept(partner_vals, address_key_list,
                                                [("parent_id", "=", parent_partner.id), ("type", "=", partner_type),
                                                 ("email", "=ilike", partner_email)])
        if not partner:
            partner = partner_obj._find_partner_ept(partner_vals, address_key_list,
                                                    [("parent_id", "=", parent_partner.id)])
        if not partner:
            partner = partner_obj._find_partner_ept(partner_vals, address_key_list)
            if partner and not partner.child_ids and partner_type == 'invoice':
                partner.write({"type": partner_type})
        if partner:
            if not partner.email:
                partner.write({"email": partner_email})
            return partner

        partner_vals.update({"type": partner_type, "parent_id": parent_partner.id, "email": partner_email})
        partner = partner_obj.create(partner_vals)

        company_name and partner.write({"company_name": company_name})
        return partner

    def shopify_prepare_partner_vals(self, vals):
        """
        This method used to prepare a partner vals.
        @param : self,vals
        @return: partner_vals
        @author: Haresh Mori @Emipro Technologies Pvt. Ltd on date 29 August 2020 .
        Task_id: 165956
        """
        partner_obj = self.env["res.partner"]

        first_name = vals.get("first_name")
        last_name = vals.get("last_name")
        name = "%s %s" % (
            first_name.strip() if first_name else first_name, last_name.strip() if last_name else last_name)

        zipcode = vals.get("zip")
        state_code = vals.get("province_code")

        country_code = vals.get("country_code")
        country = partner_obj.get_country(country_code)

        state = partner_obj.create_or_update_state_ept(country_code, state_code, zipcode, country)

        partner_vals = {
            "email": vals.get("email") or False,
            "name": name,
            "phone": vals.get("phone"),
            "street": vals.get("address1").strip() if vals.get("address1") else False,
            "street2": vals.get("address2").strip() if vals.get("address2") else False,
            "city": vals.get("city").strip() if vals.get("city") else False,
            "zip": zipcode.strip() if zipcode else False,
            "state_id": state and state.id or False,
            "country_id": country and country.id or False,
            "is_company": False
        }
        update_partner_vals = partner_obj.remove_special_chars_from_partner_vals(partner_vals)
        return update_partner_vals
