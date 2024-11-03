odoo.define('equip3_inventory_tracking.dashboard', function (require) {
    "use strict";

    var ProductExpiryDashboard = require('aspl_product_expiry_alert.dashboard').ProductExpiryDashboard;
    var AbstractAction = require('web.AbstractAction');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');

    ProductExpiryDashboard.include({
        renderElement: function () {
            var self = this;
            this._super.apply(this, arguments);
            setTimeout(function(){
               var params = {
               model: 'product.product',
               method: 'search_product_expiry',
            }
            rpc.query(params, {async: false})
            .then(function(records){
                $('.product_expiry_con').find('.ng-scope').remove();
                var links = Object.keys(records['day_wise_expire']).map(function(key) {
                    var html = "<div class='col-md-4 col-sm-6 col-xs-12 ng-scope'>";
                    html += "<div class='content' data-days='"+key+"'data-product-id='"+records['day_wise_expire'][key]['product_id']+"'>"
                    if(records['day_wise_expire'][key]['color']){

                        if(records['day_wise_expire'][key]['text_color']){
                            html += "<div class='info-box'> <span class='info-box-icon bg-aqua product_config' id='product_expiry_data' style='cursor:pointer;background-color:"+records['day_wise_expire'][key]['color']+";color:"+records['day_wise_expire'][key]['text_color']+"'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                        }
                        else{
                            html += "<div class='info-box'> <span class='info-box-icon bg-aqua product_config' id='product_expiry_data' style='cursor:pointer;background-color:"+records['day_wise_expire'][key]['color']+"'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                        }
                    }else{
                        if(records['day_wise_expire'][key]['text_color']){
                            html += "<div class='info-box'> <span class='info-box-icon bg-aqua product_config' id='product_expiry_data' style='cursor:pointer;background-color:white; color:"+records['day_wise_expire'][key]['text_color']+"'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                        }
                        else{
                            html += "<div class='info-box'> <span class='info-box-icon bg-aqua product_config' id='product_expiry_data' style='cursor:pointer;background-color:white;color:black;'>"+records['day_wise_expire'][key]['product_id'].length + "</span>";
                        }

                    }
                    html += "<div class='wrimagecard-topimage_title'> <h4>Expire In "+ key+ " Days</h4>";
                    html += "<h5 style='margin-left: 10px;margin-top: 5px;'>Total Quantity: "+ records['day_wise_expire'][key]['total_qty'] + "</h5>";
                    html += "</div></div></div>"
                    $('.product_expiry_con').append(html)
               });
               });
           });
        },
    });

});