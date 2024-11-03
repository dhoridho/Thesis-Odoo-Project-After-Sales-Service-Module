odoo.define('clear_cache', function (require) {
    'use strict';

    var core = require('web.core');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var _t = core._t;


    var ClearCache = Widget.extend({
        template: 'ClearCache',
        events: {
            'click a#clear_cache': 'clear_cache',
        },
        clear_cache: function () {
            var self = this;
            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Clear Cache'),
                views: [[false, 'form']],
                res_model: 'clear.cache.wizard',
                target: 'new',
            });
            return this.do_action
            // return this._rpc({
            //     method: 'do_clear_caches',
            //     model: 'res.users',
            // })
        }
    });
    if (odoo.debug)
        SystrayMenu.Items.push(ClearCache);

});
