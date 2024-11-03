odoo.define('equip3_general_setting.Session', function (require) {
    "use strict";
    
    var utils = require('web.utils');
    var Session = require('web.Session');
    var rpc = require('web.rpc');

    Session.include({
        setCompanies: function (main_company_id, company_ids) {
            var hash = $.bbq.getState()
            hash.cids = company_ids.sort(function(a, b) {
                if (a === main_company_id) {
                    return -1;
                } else if (b === main_company_id) {
                    return 1;
                } else {
                    return a - b;
                }
            }).join(',');
            utils.set_cookie('cids', hash.cids || String(main_company_id));
            $.bbq.pushState({'cids': hash.cids}, 0);
            
            var self = this;
            rpc.query({
                model: 'res.users',
                method: 'read_company_branches',
                args: [this.uid, main_company_id]
            }).then(function(result){
                var branches = _.map(result, o => o.id);
                var main_branch_id = _.filter(result, o => o.company_id === main_company_id)[0].id;
                self.setBranches(main_branch_id, branches);
            });
        },

        setBranches: function (main_branch_id, branch_ids) {
            var hash = $.bbq.getState()
            hash.bids = branch_ids.sort(function(a, b) {
                if (a === main_branch_id) {
                    return -1;
                } else if (b === main_branch_id) {
                    return 1;
                } else {
                    return a - b;
                }
            }).join(',');
            utils.set_cookie('bids', hash.bids || String(main_branch_id));
            $.bbq.pushState({'bids': hash.bids}, 0);
            location.reload();
        },
    });
    return Session;
});