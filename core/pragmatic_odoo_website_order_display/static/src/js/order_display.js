odoo.define('pragmatic_odoo_website_order_display.order_screen', function(require){
'use strict';
    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var translation = require('web.translation');
    var _t = translation._t;


    $(document).ready(function(){

        bind_page_element_events();

        // Refresh order display screen after one minute
        const order_display_screen_refresh = setInterval(ajax_call_all_time, 60000);
        if (!location.pathname.includes('/page/order/display')) {
			clearInterval(order_display_screen_refresh);
		}
    });

    function bind_page_element_events(){
        $('.start-btn').off().on('click', _start_click_handler);
        $('.complete-btn').off().on('click', _complete_click_handler);
        $('#orderList').on('hide.bs.collapse', _hide_collapse);
        $('#orderList').on('show.bs.collapse', _show_collapse);
    }

    var ajax_call_all_time = function(){
        $.ajax({
            type:    "GET",
            url : location.pathname,
//				data : value,
            cache : "false",
            success : function(res) {
                $("#orderList").html($(res).find("#orderList").html())
                // Bind page events on screen refresh
                bind_page_element_events();
            },Error : function(x, e) {
                alert("Some error");
            }
        });
    }

    function update_order(data){
        var $def =  $.Deferred();
        ajax.jsonRpc('/order/update', 'call', data)
        .then(function (result) {
            $def.resolve(result);
        }).guardedCatch(function () {
            console.error('Failed to update order:', data.order_id);
            $def.reject();
        });

        return $def;
    }

    function _start_click_handler(ev){
        ev.preventDefault();
        ev.stopPropagation();
        let $start_btn = $(this);
        const order_id = $start_btn.parent().data("order_id");
        let $complete_btn = $('#complete-btn-'+order_id);
        let data = {'order_id': order_id, 'state': 'progress'}
        $.blockUI({ message: '' , overlayCSS: {'z-index': 9999, backgroundColor: '#FFFFFF', opacity: 0.0, cursor: 'wait'}});
        update_order(data).then(function(id){
            $.unblockUI();
            $start_btn.delay(300).fadeOut('slow',function(){
                $(this).hide();
            });
            $complete_btn.delay(500).fadeIn('slow',function(){
                $(this).show();
            });
        }).fail(function(err){
            console.log(err);
            $.unblockUI();
        });
    }

    function _complete_click_handler(ev){
        ev.preventDefault();
        ev.stopPropagation();
        let $complete_btn = $(this);
        const order_id = $complete_btn.parent().data("order_id");
//        let $card = $('#card-'+order_id);
        let $done = $('#done-'+order_id);
        let data = {'order_id': order_id, 'state': 'ready'}
        $.blockUI({ message: '' , overlayCSS: {'z-index': 9999, backgroundColor: '#FFFFFF', opacity: 0.0, cursor: 'wait'}});
        update_order(data).then(function(id){
            $.unblockUI();
            $complete_btn.delay(300).fadeOut('slow',function(){
                $(this).hide();
            });
            $done.delay(500).fadeIn('slow',function(){
                $(this).show();
            });
        }).fail(function(err){
            console.log(err);
            $.unblockUI();
        });
    }

    function _hide_collapse(ev){
        const $i = $(ev.target).siblings('.card-header').find('h5 > i');
        if($i.hasClass('fa-minus')){
            $i.removeClass('fa-minus').addClass('fa-plus');
        }
    }

    function _show_collapse(ev){
        const $i = $(ev.target).siblings('.card-header').find('h5 > i');
        if($i.hasClass('fa-plus')){
            $i.removeClass('fa-plus').addClass('fa-minus');
        }

    }

});