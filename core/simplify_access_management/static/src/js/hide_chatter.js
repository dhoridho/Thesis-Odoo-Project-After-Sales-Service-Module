odoo.define('simplify_access_management.hide_chatter', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var session = require("web.Session");
    var rpc = require('web.rpc');

    FormRenderer.include({
        _render: async function () {
            const res = await this._super.apply(this, arguments);
            const self = this;
            // this._super.apply(this, arguments);
            var hash = window.location.hash.replace("#", '').split("&");
            let cids;
            if(hash.findIndex(ele => ele.includes("cid")) == -1)
                cids = session.company_id;
            else {
                cids = hash.filter(ele => ele.includes("cid"))[0].split("=")[1].split(",");
                cids = cids.length > 0? parseInt(cids[0]): session.company_id;
            }
            let model = hash.filter(ele=>ele.includes("model"))?.[0];
            model = model? model.split("=")?.[1].split(",")?.[0]: model;
            if(cids && model) {
                rpc.query({
                    model:'access.management',
                    method: 'get_chatter_hide_details',
                    args: [cids, model]
                }).then(function(result){
                    if(result['hide_send_mail'] == false)
                    {
                        var btn1 = setInterval(function() {
                        if ($('.o_ChatterTopbar_buttonSendMessage').length) {
                                $('.o_ChatterTopbar_buttonSendMessage').remove();
                                clearInterval(btn1);
                        }
                        }, 50);
                    }
                    if(result['hide_log_notes'] == false)
                    {
                        var btn2 = setInterval(function() {
                        if ($('.o_ChatterTopbar_buttonLogNote').length) {
                                $('.o_ChatterTopbar_buttonLogNote').remove();
                                clearInterval(btn2);
                        }
                        }, 50);
                    }
                    if(result['hide_schedule_activity'] == false)
                    {
                        var btn3 = setInterval(function() {
                        if ($('.o_ChatterTopbar_buttonScheduleActivity').length) {
                                $('.o_ChatterTopbar_buttonScheduleActivity').remove();
                                clearInterval(btn3);
                        }
                        }, 50);
                    }

                });
            }
            return res;
        },
    });
});