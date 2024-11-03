odoo.define('equip3_pos_price_checker.kiosk_mode', function(require) {
    var AbstractAction = require('web.AbstractAction');
	var ajax = require('web.ajax');
	var core = require('web.core');
	var Session = require('web.session');
	var KioskMode = require('sh_price_checker_kiosk.kiosk_mode')
	var QWeb = core.qweb;


    KioskMode.include({

        events: _.extend({}, KioskMode.prototype.events, {
            "keyup input[name='code']#code": function(event){ 
                $('#screen_delay').val(60)
                if ( event.keyCode === 13 ) {
                    $('.o_mrp_kiosk_button_done').click()
                }
            },
            "click button.o_mrp_kiosk_button_done": function(){ 
                var mo_no = $("#code").val();
                var self = this
                if(mo_no){
                    var stop = false
                    var timeout = setTimeout(function()
                    {
                        if($('th#th_pricelist').length > 0){
                            $('table#product_detail_table').css({ fontFamily : "Lato"});
                            clearTimeout(timeout);
                            self._rpc({
                                model: 'product.product',
                                method: 'all_scan_search_pos_price_checker',
                                args: [mo_no],
                            })
                            .then(function (result) {
                                $('#tr_wh_wtock').remove()
                                if(result && 'quant_result' in result){
                                    var $parent = $($('th#th_pricelist').parent())
                                    var content_stock = '<div>'
                                    for(var i = 0; i < result['quant_result'].length; i++){
                                        var quant = result['quant_result'][i]
                                        content_stock+= `
                                                    <div style="display: inline-flex; width: 100%; border-bottom: 1px solid #dddddd;margin-bottom:10px;">
                                                        <div style="width: 60%;">
                                                        <p style="margin:0px;color: gray;">`+quant['name']+`</p>
                                                        </div>
                                                        <div style="width: 40%; text-align: right;">
                                                        <p style="margin:0px;color: gray;padding-right: 10px;">`+quant['qty']+`</p>
                                                        </div>
                                                    </div>
                                        `
                                    }
                                    content_stock+='</div>'
                                    var table_stock = `
                                    <tr id="tr_wh_wtock">
                                        <th width="30%" id="th_wh_stock">Warehouse <br> Stock</th>
                                        <td width="70%" align="left" id="sh_wh_stock">`+content_stock+`</td>
                                    </tr>`

                                    $(table_stock).insertAfter($parent);
                                }
                                if(result && 'need_image_default' in result){
                                    $('#sh_product_image').html('');
                                    $('#sh_product_image').append(
                                            '<img class="img img-responsive" width="auto !important;" style="max-height:100%;max-width:100%;" src="'+result['need_image_default']+'" alt="Product Image" />'
                                    );
                                }
                                                                                                                                                   
                            }); 

                        } 
                    }, 1000);
                }
            }
        }),

        

    });


});