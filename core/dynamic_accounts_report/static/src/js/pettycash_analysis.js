odoo.define('equip3_accounting_reports.pettycash_analysis', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var _t = core._t;
    var data_entp = [];

    window.click_num = 0;

    var pettycash_analysis = AbstractAction.extend({
        template: 'pettycash_analysis',
            

    });
    core.action_registry.add('ent_p', pettycash_analysis);
    return pettycash_analysis;
});







