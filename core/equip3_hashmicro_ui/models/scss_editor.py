
import re
import uuid
import base64

from odoo import models, fields, api
from odoo.modules import module


XML_ID = "equip3_hashmicro_ui._assets_primary_variables"
SCSS_URL = "/equip3_hashmicro_ui/static/src/scss/colors.scss"


class ScssEditor(models.AbstractModel):
    _name = 'equip3_hashmicro_ui.scss_editor'
    _description = 'Scss Editor'

    # ----------------------------------------------------------
    # Helper
    # ----------------------------------------------------------

    def _build_custom_url(self, url_parts, xmlid):
        return "%s.custom.%s.%s" % (url_parts[0], xmlid, url_parts[1])

    def _get_custom_url(self, url, xmlid):
        return self._build_custom_url(url.rsplit(".", 1), xmlid)

    def _get_custom_attachment(self, url):
        return self.env["ir.attachment"].with_context(
            bin_size=False, bin_size_datas=False
        ).search([("url", '=', url)], limit=1)

    def _get_custom_view(self, url):
        return self.env["ir.ui.view"].search([("name", '=', url)])

    def _get_variable(self, content, variable):
        regex = r'{0}\s*:\s*(.*?);'.format(variable)
        value = re.search(regex, content)
        return value and value.group(1)

    def _get_variables(self, content, variables):
        return {var: self._get_variable(content, var) for var in variables}

    def _replace_variables(self, content, variables):
        for variable in variables:
            variable_content = '{0}: {1};'.format(
                variable['name'],
                variable['value']
            )
            regex = r'{0}\s*:\s*(.*?);'.format(variable['name'])
            content = re.sub(regex, variable_content, content)
        return content

    # ----------------------------------------------------------
    # Read
    # ----------------------------------------------------------

    def get_content(self, url, xmlid):
        custom_url = self._get_custom_url(url, xmlid)
        custom_attachment = self._get_custom_attachment(custom_url)
        if custom_attachment.exists():
            return base64.b64decode(custom_attachment.datas).decode('utf-8')
        else:
            match = re.compile("^/(\w+)/(.+?)(\.custom\.(.+))?\.(\w+)$").match(url)
            module_path = module.get_module_path(match.group(1))
            resource_path = "%s.%s" % (match.group(2), match.group(5))
            module_resource_path = module.get_resource_path(module_path, resource_path)
            with open(module_resource_path, "rb") as file:
                return file.read().decode('utf-8')

    def get_values(self, url, xmlid, variables):
        content = self.get_content(url, xmlid)
        return self._get_variables(content, variables)

    # ----------------------------------------------------------
    # Write
    # ----------------------------------------------------------

    def replace_content(self, url, xmlid, content):
        custom_url = self._get_custom_url(url, xmlid)
        custom_view = self._get_custom_view(custom_url)
        custom_attachment = self._get_custom_attachment(custom_url)
        datas = base64.b64encode((content or "\n").encode("utf-8"))
        if custom_attachment.exists():
            custom_attachment.write({"datas": datas})
        else:
            self.env["ir.attachment"].create({
                'name': custom_url,
                'type': "binary",
                'mimetype': "text/scss",
                'datas': datas,
                # TODO: old field datas_fname got removed, check if store_fname is correct and write migration
                'store_fname': url.split("/")[-1],
                'url': custom_url,
            })
        if not custom_view.exists():
            view_to_xpath = self.env["ir.ui.view"].get_related_views(
                xmlid, bundles=True
            ).filtered(lambda v: v.arch.find(url) >= 0)
            if not view_to_xpath:
                return
            self.env["ir.ui.view"].create({
                'name': custom_url,
                'key': 'web_editor.scss_%s' % str(uuid.uuid4())[:6],
                'mode': "extension",
                'priority': view_to_xpath.priority,
                'inherit_id': view_to_xpath.id,
                'type': 'qweb',
                'arch': """
                    <data inherit_id="%(inherit_xml_id)s" name="%(name)s">
                        <xpath expr="//link[@href='%(url_to_replace)s']" position="attributes">
                            <attribute name="href">%(new_url)s</attribute>
                        </xpath>
                    </data>
                """ % {
                    'inherit_xml_id': view_to_xpath.xml_id,
                    'name': custom_url,
                    'url_to_replace': url,
                    'new_url': custom_url,
                }
            })
        self.env["ir.qweb"].clear_caches()

    def replace_values(self, url, xmlid, variables):
        content = self._replace_variables(
            self.get_content(url, xmlid), variables
        )
        self.replace_content(url, xmlid, content)

    def reset_values(self, url, xmlid):
        custom_url = self._get_custom_url(url, xmlid)
        self._get_custom_attachment(custom_url).unlink()
        self._get_custom_view(custom_url).unlink()

    @api.model
    def upgrade_scss(self):
        custom_url = self.env['equip3_hashmicro_ui.scss_editor']._get_custom_url(SCSS_URL, XML_ID)
        custom_attachment = self.env['equip3_hashmicro_ui.scss_editor']._get_custom_attachment(custom_url)
        if custom_attachment.exists():
            custom_attachment.unlink()
        config_id = self.env['sh.back.theme.config.settings'].sudo().search([], limit=1)
        if config_id:
            self.env['res.users'].change_theme_color({'color': config_id.equip_theme_color})
