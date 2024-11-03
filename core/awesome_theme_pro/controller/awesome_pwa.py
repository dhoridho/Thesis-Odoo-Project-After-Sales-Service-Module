# -*- coding: utf-8 -*-
from odoo.http import Controller, request, route


class PWA(Controller):
    '''
    PWA supports
    '''

    def get_asset_urls(self, asset_xml_id):
        '''
        get the asset urls
        :param asset_xml_id:
        :return:
        '''
        qweb = request.env["ir.qweb"].sudo()
        assets = qweb._get_asset_nodes(asset_xml_id, {}, True, True)
        urls = []
        for asset in assets:
            if asset[0] == "link":
                urls.append(asset[1]["href"])
            if asset[0] == "script":
                urls.append(asset[1]["src"])
        return urls

    @route("/awesome-service-worker.js", type="http", auth="public")
    def service_worker(self):
        '''
        service worker
        :return:
        '''
        qweb = request.env["ir.qweb"].sudo()
        urls = []
        urls.extend(self.get_asset_urls("web.assets_common"))
        urls.extend(self.get_asset_urls("web.assets_backend"))
        version_list = []
        for url in urls:
            version_list.append(url.split("/")[3])
        cache_version = "-".join(version_list)
        mimetype = "text/javascript;charset=utf-8"
        content = qweb._render(
            "awesome_theme_pro.service_worker", {
                "awesome_pwa_cache_name": cache_version,
                "awesome_pwa_files_to_cache": urls
            },
        )
        return request.make_response(content, [("Content-Type", mimetype)])

    @route("/awesome_theme_pro/manifest.json", type="http", auth="public")
    def manifest(self):
        '''
        :return: return the manifest
        '''
        qweb = request.env["ir.qweb"].sudo()

        # get the extra style data
        user_setting = \
            request.env["awesome_theme_pro.theme_setting_manager"].sudo().get_user_setting(
                get_mode_data=False,
                get_style_txt=False)

        settings = user_setting["settings"]
        pwa_name = settings["pwa_name"]
        pwa_short_name = settings["pwa_short_name"]

        icon128x128 = settings.get("icon128_url", False)
        icon144x144 = settings.get("icon144_url", False)
        icon152x152 = settings.get("icon152_url", False)
        icon192x192 = settings.get("icon192_url", False)
        icon256x256 = settings.get("icon256_url", False)
        icon512x512 = settings.get("icon512_url", False)

        pwa_background_color = settings["pwa_background_color"]
        pwa_theme_color = settings["pwa_theme_color"]

        mimetype = "application/json;charset=utf-8"

        content = qweb._render("awesome_theme_pro.manifest", {
            "pwa_name": pwa_name,
            "pwa_short_name": pwa_short_name,
            "icon128x128": icon128x128,
            "icon144x144": icon144x144,
            "icon152x152": icon152x152,
            "icon192x192": icon192x192,
            "icon256x256": icon256x256,
            "icon512x512": icon512x512,
            "background_color": pwa_background_color,
            "theme_color": pwa_theme_color,
        })

        return request.make_response(content, [("Content-Type", mimetype)])
