# pip install pymemcache

from odoo import models, api
from pymemcache.client.base import Client
from pymemcache.exceptions import MemcacheUnknownError
import logging

_logger = logging.getLogger(__name__)


# What to cache and respective expiry in seconds
CACHE_TEMPLATES = {
    'website.submenu': {'expiry': 20},
    'web.assets_common': {'expiry': 20},
    'web.assets_frontend': {'expiry': 20},
    'base.contact': {'expiry': 20},
    'website_blog.blog_post_short': {'expiry': 20},
    'website.contactus': {'expiry': 20},
    # This was a template that I tried and ended up creating problems
    # But try to uncomment and check what happens to product image
    # 'website_sale.shop_product_carousel': {'expiry': 1200},
    'website_sale.product': {'expiry': 20},
    'website_sale.products': {'expiry': 20},
    'website.500': {'expiry': 20},
}

# MEMCACHED_SETTINGS = False
# MEMCACHED_SETTINGS = Client(('localhost', 11211))
MEMCACHED_SETTINGS = Client('/tmp/memcached.sock')


class QWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def render(self, template, values=None, **options):
        """
        to fine tune use --log-handler "odoo.addons.website_cache:DEBUG"

        :param template:
        :param values:
        :param options:
        :return:
        """
        if not MEMCACHED_SETTINGS:
            return super(QWeb, self).render(template, values, **options)
        if isinstance(template, int):
            template_key = self.env['ir.ui.view'].browse(template).key
        else:
            template_key = template
        settings = CACHE_TEMPLATES.get(template_key, False)
        user_id = values.get('user_id', False)
        if settings and user_id:
            request = values.get('request', False)
            env = values.get('env', False)
            lang = values.get('lang', False)
            if user_id.id == env.ref('base.public_partner').id:
                cache_result = False
                cache_key = "%(lang)s%(url)s" % {'url': request.httprequest.url, 'template_id': template_key, 'lang': lang}
                for origin, target in [('http:', ''), ('https:', ''), ('/', '_')]:
                    cache_key = cache_key.replace(origin, target)
                client = MEMCACHED_SETTINGS
                try:
                    cache_result = client.get(cache_key)
                except MemcacheUnknownError as e:
                    _logger.error("WEBSITE_CACHE: Failed getting key from cache %s" % cache_key)

                if cache_result:
                    _logger.debug("WEBSITE_CACHE: Getting from cache %s" % cache_key)
                    return cache_result
                else:
                    content = super(QWeb, self).render(template, values, **options)
                    expiry = int(settings.get('expiry', 0))
                    client.set(cache_key, content, expiry)
                    _logger.debug("WEBSITE_CACHE: Adding to cache %s" % cache_key)
                    return content
            else:
                _logger.debug("WEBSITE_CACHE: No user, no caching at all - template: %s" % template_key)
                return super(QWeb, self).render(template, values, **options)
        else:
            _logger.debug("WEBSITE_CACHE: Not caching at all - template: %s" % template_key)
            return super(QWeb, self).render(template, values, **options)