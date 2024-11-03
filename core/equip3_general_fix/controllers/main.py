from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.base.models.assetsbundle import JavascriptAsset
from odoo.addons.base.models.assetsbundle import StylesheetAsset
import os
from collections import OrderedDict
from odoo import fields, tools, SUPERUSER_ID
from odoo.http import request
from odoo.tools import func, misc




def to_node(self, css=True, js=True, debug=False, async_load=False, defer_load=False, lazy_load=False):
    response = []
    if debug and 'assets' in debug:
        if css and self.stylesheets:
            is_css_preprocessed, old_attachments = self.is_css_preprocessed()
            if not is_css_preprocessed:
                self.preprocess_css(debug=debug, old_attachments=old_attachments)
                if self.css_errors:
                    msg = '\n'.join(self.css_errors)
                    response.append(JavascriptAsset(self, inline=self.dialog_message(msg)).to_node())
                    response.append(StylesheetAsset(self, url="/web/static/lib/bootstrap/css/bootstrap.css").to_node())
            if not self.css_errors:
                for style in self.stylesheets:
                    response.append(style.to_node())

        if js:
            for jscript in self.javascripts:
                response.append(jscript.to_node())
    else:
        if css and self.stylesheets:
            css_attachments = self.css() or []
            for attachment in css_attachments:
                attr = OrderedDict([
                    ["type", "text/css"],
                    ["rel", "stylesheet"],
                    ["href", attachment.url],
                    ['data-asset-xmlid', self.name],
                    ['data-asset-version', self.version],
                ])
                response.append(("link", attr, None))
            if self.css_errors:
                msg = '\n'.join(self.css_errors)
                response.append(JavascriptAsset(self, inline=self.dialog_message(msg)).to_node())
        if js and self.javascripts:
            if self.name == 'web.assets_backend':
                async_load = True
            attr = OrderedDict([
                ["async", "async" if async_load else None],
                ["defer", "defer" if defer_load or lazy_load else None],
                ["type", "text/javascript"],
                ["data-src" if lazy_load else "src", self.js().url],
                ['data-asset-xmlid', self.name],
                ['data-asset-version', self.version],
            ])
            response.append(("script", attr, None))

    return response


AssetsBundle.to_node = to_node