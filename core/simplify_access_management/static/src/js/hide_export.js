odoo.define('simplify_access_management.hide_export', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var session = require("web.Session");
    var rpc = require('web.rpc');


    function toHex(str) {
        return str.split('').map(c => c.charCodeAt(0).toString(16)).join('');
    }

    function fromHex(hex) {
        let str = '';
        for (let i = 0; i < hex.length; i += 2) {
            // Get the substring of two characters (one byte)
            const byte = hex.substr(i, 2);
            // Convert hex to decimal and then to the corresponding character
            str += String.fromCharCode(parseInt(byte, 16));
        }
        return str;
    }

    ListRenderer.include({

        _render: function () {
            const res = this._super.apply(this, arguments);
            const self = this;
            this._super.apply(this, arguments);
            
            
            if (window.location.hash.includes('hashcode')){
                var hash = $.bbq.getState(false)
                var model = false
                var hashcode = fromHex(decodeURIComponent(hash.hashcode))
                var cids = session.company_id
                if(hashcode.includes('cids=')){
                    cids = (hashcode.match(/cids=([^&]*)/)[1]).split(",");
                }
                if(hashcode.includes('model=')){
                    var model = hashcode.match(/model=([^&]*)/)[1];
                }
            }
            else{
                var hash = window.location.hash.replace("#", '').split("&");
                var cids;
                if(hash.findIndex(ele => ele.includes("cid")) == -1)
                    cids = session.company_id;
                else {
                    cids = hash.filter(ele => ele.includes("cid"))[0].split("=")[1].split(",");
                    cids = cids.length > 0? parseInt(cids[0]): session.company_id;
                }
                var model = hash.filter(ele=>ele.includes("model"))?.[0];
                model = model? model.split("=")?.[1].split(",")?.[0]: model;
            }
            
            if(cids && model) {
                rpc.query({
                    model:'access.management',
                    method: 'is_export_n_upload_hide',
                    args: [cids, model]
                }).then(function(result){
                    console.log(result,'result')
                    if(result[0]) {
                        var btn1 = setInterval(function() {
                        if ($('.o_list_export_xlsx').length) {
                                $('.o_list_export_xlsx').remove();
                                clearInterval(btn1);
                        }
                        }, 50);
                    }
                    if(result[1]) {
                        var btn1 = setInterval(function() {
                        if ($('.o_list_buttons .o_button_upload_bill').length) {
                                $('.o_list_buttons .o_button_upload_bill').remove();
                                clearInterval(btn1);
                        }
                        }, 50);
                    }
                });
            }
            return res;

        },

    });

});