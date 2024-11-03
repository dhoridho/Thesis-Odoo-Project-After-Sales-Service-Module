odoo.define('equip3_pos_masterdata.SplitBillScreen', function (require) {
    'use strict';

    const SplitBillScreen = require('pos_restaurant.SplitBillScreen');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    const RetailSplitBillScreen = (SplitBillScreen) =>
        class extends SplitBillScreen {
            constructor() {
                super(...arguments);

            }

            back() {
                super.back()
                posbus.trigger('set-screen', 'Products')
            }

            add_qty(){
                var self = this
                let order = this.env.pos.get_order();
                var currency = false
                if(order){
                    currency = order.currency
                }
                var total_order = order.get_total_with_tax()
                var page_active_name = $('.splitbillscreen_content_button .button.active').text()
                if (page_active_name.indexOf("Split Per Pax") >= 0){
                    var value = parseInt($('input#number_person_split').val())
                    value += 1 
                    $('input#number_person_split').val(value)
                    $('#price_person_split').text(this.env.pos.format_currency(order.get_total_with_tax()/value,false,currency))
                }
                if (page_active_name.indexOf("Split By Percentage") >= 0){
                    var value = parseInt($('input#number_percentage_split').val())
                    value += 1 
                    $('input#number_percentage_split').val(value)
                    $('li.custom_line_percentage_split').remove()
                    for (var i = 0; i < value; i++) {
                        var htmladd = '\
                        <li class="orderline custom_line_percentage_split">\
                                        <div class="row_item_split">\
                                            <div class="split_item_left">\
                                                <p style="margin:unset;font-size: 21px;margin-bottom: 10px;">\
                                                    <b>Input Percentage</b>\
                                                </p>\
                                                <p style="margin:unset;font-size: 21px;margin-bottom: 10px;min-height: 15px;">\
                                                    <b class="amount_from_percentage"></b>\
                                                </p>\
                                                <br/>\
                                            </div>\
                                            <div class="split_item_right" style="display:block;position:relative;">\
                                                <ul style="width: 100%;" >\
                                                    <li style="color:white;">------</li>\
                                                    <li aria-label="Up Qty 1" role="img" title="Up Qty 1" class="faupdown oe_link_icon fa fa-plus oe_icon line-icon" t-on-click="add_qty"></li>\
                                                     <li><input type="number" class="input_percentage_split" value="0" min="1" /></li>\
                                                     <li aria-label="Down Qty 1" t-on-click="min_qty" role="img" title="Down Qty 1" class="faupdown oe_link_icon fa fa-minus oe_icon line-icon"></li>\
                                                </ul>\
                                            </div>\
                                        </div>\
                                    </li>'
                        $( ".ul_split_bill_percentage" ).append( htmladd );

          
                    }
                    $('.custom_line_percentage_split .faupdown').unbind('click');
                    $('.custom_line_percentage_split .faupdown').bind('click', function() { 
                        var value = parseFloat($($(this).parent()).find('input').val())
                        if($(this).attr('title')=='Up Qty 1') {
                            
                            $($(this).parent()).find('input').val(value+1)
                        }
                        if($(this).attr('title')=='Down Qty 1') {
                            if (value > 0){
                                $($(this).parent()).find('input').val(value-1)
                            }
                                
                        }
                        var amount_from_percentage = self.env.pos.format_currency((total_order/100)*value,false,currency)
                        $($(this).parents()[3]).find('.amount_from_percentage').text(amount_from_percentage)
                        
                    });
                    $('.custom_line_percentage_split input').unbind('change');
                    $('.custom_line_percentage_split input').bind('change', function() { 
                        var value = parseFloat($(this).val())
                        var amount_from_percentage = self.env.pos.format_currency((total_order/100)*value,false,currency)
                        $($(this).parents()[3]).find('.amount_from_percentage').text(amount_from_percentage)
                        
                    });
                        
                    
                
                }
                if (page_active_name.indexOf("Split By Total Amount") >= 0){
                    var value = parseInt($('input#number_amount_split').val())
                    value += 1 
                    $('input#number_amount_split').val(value)

                    $('li.custom_line_amount_split').remove()
                    for (var i = 0; i < value; i++) {
                        var htmladd = '\
                        <li class="orderline custom_line_amount_split">\
                                        <div class="row_item_split">\
                                            <div class="split_item_left">\
                                                <p style="margin:unset;font-size: 21px;margin-bottom: 10px;">\
                                                    <br/>\
                                                    <b>Input Amount</b>\
                                                </p>\
                                                <br/>\
                                            </div>\
                                            <div class="split_item_right" style="display:block;position:relative;">\
                                                <ul style="width: 100%;" >\
                                                    <li style="color:white;">------</li>\
                                                    <li aria-label="Up Qty 1" role="img" title="Up Qty 1" class="faupdown oe_link_icon fa fa-plus oe_icon line-icon" t-on-click="add_qty"></li>\
                                                     <li><input type="number" class="input_amount_split" value="0" min="1" /></li>\
                                                     <li aria-label="Down Qty 1" t-on-click="min_qty" role="img" title="Down Qty 1" class="faupdown oe_link_icon fa fa-minus oe_icon line-icon"></li>\
                                                </ul>\
                                            </div>\
                                        </div>\
                                    </li>'
                        $( ".ul_split_bill_amount" ).append( htmladd );
                    }

                    $('.custom_line_amount_split .faupdown').unbind('click');
                        $('.custom_line_amount_split .faupdown').bind('click', function() { 
                            var value = parseFloat($($(this).parent()).find('input').val())
                            if($(this).attr('title')=='Up Qty 1') {
                                
                                $($(this).parent()).find('input').val(value+1)
                            }
                            if($(this).attr('title')=='Down Qty 1') {
                                if (value > 0){
                                    $($(this).parent()).find('input').val(value-1)
                                }
                                    
                            }
                        });
                        
                       
                
                }
                
            }


            min_qty(){
                var self = this
                let order = this.env.pos.get_order();
                var currency = false
                if(order){
                    currency = order.currency
                }
                var total_order = order.get_total_with_tax()
                var page_active_name = $('.splitbillscreen_content_button .button.active').text()
                if (page_active_name.indexOf("Split Per Pax") >= 0){
                    var value = parseInt($('input#number_person_split').val())
                    if (value>1) {
                        value -= 1 
                    }
                    $('input#number_person_split').val(value)
                    $('#price_person_split').text(this.env.pos.format_currency(order.get_total_with_tax()/value,false,currency))
                }
                if (page_active_name.indexOf("Split By Percentage") >= 0){
                    var value = parseInt($('input#number_percentage_split').val())
                    if (value>1) {
                        value -= 1 
                    }
                    $('input#number_percentage_split').val(value)
                    $('li.custom_line_percentage_split').remove()
                    for (var i = 0; i < value; i++) {
                        var htmladd = '\
                        <li class="orderline custom_line_percentage_split">\
                                        <div class="row_item_split">\
                                            <div class="split_item_left">\
                                                <p style="margin:unset;font-size: 21px;margin-bottom: 10px;">\
                                                    <b>Input Percentage</b>\
                                                </p>\
                                                <p style="margin:unset;font-size: 21px;margin-bottom: 10px;min-height: 15px;">\
                                                    <b class="amount_from_percentage"></b>\
                                                </p>\
                                                <br/>\
                                            </div>\
                                            <div class="split_item_right" style="display:block;position:relative;">\
                                                <ul style="width: 100%;" >\
                                                    <li style="color:white;">------</li>\
                                                    <li aria-label="Up Qty 1" role="img" title="Up Qty 1" class="faupdown oe_link_icon fa fa-plus oe_icon line-icon" t-on-click="add_qty"></li>\
                                                     <li><input type="number" class="input_percentage_split" value="0" min="1" /></li>\
                                                     <li aria-label="Down Qty 1" t-on-click="min_qty" role="img" title="Down Qty 1" class="faupdown oe_link_icon fa fa-minus oe_icon line-icon"></li>\
                                                </ul>\
                                            </div>\
                                        </div>\
                                    </li>'
                        $( ".ul_split_bill_percentage" ).append( htmladd );

                    }
                    $('.custom_line_percentage_split .faupdown').unbind('click');
                    $('.custom_line_percentage_split .faupdown').bind('click', function() { 
                        var value = parseFloat($($(this).parent()).find('input').val())
                        if($(this).attr('title')=='Up Qty 1') {
                            
                            $($(this).parent()).find('input').val(value+1)
                        }
                        if($(this).attr('title')=='Down Qty 1') {
                            if (value > 0){
                                $($(this).parent()).find('input').val(value-1)
                            }
                                
                        }
                        var amount_from_percentage = self.env.pos.format_currency((total_order/100)*value,false,currency)
                        $($(this).parents()[3]).find('.amount_from_percentage').text(amount_from_percentage)
                        
                    });
                    $('.custom_line_percentage_split input').unbind('change');
                    $('.custom_line_percentage_split input').bind('change', function() { 
                        var value = parseFloat($(this).val())
                        var amount_from_percentage = self.env.pos.format_currency((total_order/100)*value,false,currency)
                        $($(this).parents()[3]).find('.amount_from_percentage').text(amount_from_percentage)
                        
                    });
                        
                }
                if (page_active_name.indexOf("Split By Total Amount") >= 0){
                    var value = parseInt($('input#number_amount_split').val())
                    if (value>1) {
                        value -= 1 
                    }
                    $('input#number_amount_split').val(value)
                    $('li.custom_line_amount_split').remove()
                    for (var i = 0; i < value; i++) {
                        var htmladd = '\
                        <li class="orderline custom_line_amount_split">\
                                        <div class="row_item_split">\
                                            <div class="split_item_left">\
                                                <p style="margin:unset;font-size: 21px;margin-bottom: 10px;">\
                                                    <br/>\
                                                    <b>Input Amount</b>\
                                                </p>\
                                                <br/>\
                                            </div>\
                                            <div class="split_item_right" style="display:block;position:relative;">\
                                                <ul style="width: 100%;" >\
                                                    <li style="color:white;">------</li>\
                                                    <li aria-label="Up Qty 1" role="img" title="Up Qty 1" class="faupdown oe_link_icon fa fa-plus oe_icon line-icon" t-on-click="add_qty"></li>\
                                                     <li><input type="number" class="input_amount_split" value="0" min="1" /></li>\
                                                     <li aria-label="Down Qty 1" t-on-click="min_qty" role="img" title="Down Qty 1" class="faupdown oe_link_icon fa fa-minus oe_icon line-icon"></li>\
                                                </ul>\
                                            </div>\
                                        </div>\
                                    </li>'
                        $( ".ul_split_bill_amount" ).append( htmladd );
                    }
                    $('.custom_line_amount_split .faupdown').unbind('click');
                        $('.custom_line_amount_split .faupdown').bind('click', function() { 
                            var value = parseFloat($($(this).parent()).find('input').val())
                            if($(this).attr('title')=='Up Qty 1') {
                                
                                $($(this).parent()).find('input').val(value+1)
                            }
                            if($(this).attr('title')=='Down Qty 1') {
                                if (value > 0){
                                    $($(this).parent()).find('input').val(value-1)
                                }
                                    
                            }
                        });
                }
            }

            _initSplitLines(order) {
                const splitlines = {};
                for (let line of order.get_orderlines()) {
                    splitlines[line.id] = { product: line.get_product().id, quantity: line.quantity,max_qty:line.quantity };
                }
                return splitlines;
            }
            async splitbuttonprocess(number) {
                $('.splitbillscreen_content_button .button').removeClass('active')
                $($('.splitbillscreen_content_button .button')[number-1]).addClass('active')
                $('.page_split_screen').removeClass('active')
                $($('.page_split_screen')[number-1]).addClass('active')
            }

            onClickLine(event) {
            const line = event.detail;
                this._splitQuantity(line);
                this._updateNewOrder(line);
            }

            _setQuantityOnCurrentOrder() {
                let order = this.env.pos.get_order();
                for (var id in this.splitlines) {
                    var split = this.splitlines[id];
                    var line = this.currentOrder.get_orderline(parseInt(id));

                    if(!this.props.disallow) {
                        line.set_quantity(
                            line.get_quantity() - split.quantity,
                            'do not recompute unit price'
                        );
                        if (Math.abs(line.get_quantity()) < 0.00001) {
                            this.currentOrder.remove_orderline(line);
                        }
                    } else {
                        if(split.quantity) {
                            let decreaseLine = line.clone();
                            decreaseLine.order = order;
                            decreaseLine.noDecrease = true;
                            decreaseLine.set_quantity(-split.quantity);
                            order.add_orderline(decreaseLine);
                        }
                    }
                }
            }

            _splitQuantity(line) {
                const split = this.splitlines[line.id];
                let totalQuantity = 0;

                this.env.pos.get_order().get_orderlines().forEach(function(orderLine) {
                    if(orderLine.get_product().id === split.product)
                        totalQuantity += orderLine.get_quantity();
                });
                // if(line.get_quantity() > 0 && split.quantity) {
                //     split.quantity = line.get_quantity() - split.quantity
                // }

                // if(line.get_quantity() > 0) {
                //     if (!line.get_unit().is_pos_groupable) {
                //         if (split.quantity !== line.get_quantity()) {
                //             split.quantity = line.get_quantity();
                //         } else {
                //             split.quantity = 0;
                //         }
                //     } 
                //     else {
                //         if (split.quantity < totalQuantity) {
                //             split.quantity += line.get_unit().is_pos_groupable? 1: line.get_unit().rounding;
                //             if (split.quantity > line.get_quantity()) {
                //                 split.quantity = line.get_quantity();
                //             }
                //         } else {
                //             split.quantity = 0;
                //         }
                //     }
                // }
            }

            async proceed() {
                let order = this.env.pos.get_order();
                var currency = false
                if (order){
                    currency = order.currency
                }
                var page_active_name = $('.splitbillscreen_content_button .button.active').text()
                if (_.isEmpty(this.splitlines))
                    // Splitlines is empty
                    return;
                let {confirmed, payload: confirm} = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Confirmed Split'),
                    body: this.env._t('So, Are you want Split, if Yes please click Yes button'),
                    confirmText: this.env._t('Yes'),
                    cancelText: this.env._t('No')
                })
                if (confirmed) {
                    
                    if (page_active_name.indexOf("Split By Percentage") >= 0){
                        order.paymentlines.models.forEach(function (p) {
                            order.remove_paymentline(p)
                            
                        });

                        var total_order = order.get_total_with_tax()
                        var total_pay = 0
                        $('.input_percentage_split').each(function( index ) {
                            total_pay+=parseFloat($( this ).val())
                        });
                        if (100!=total_pay){
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning !'),
                                body: this.env._t('Please input total split percentage payment must be 100%')
                            })
                        }
                            
                        
                        var cash_method = _.find(this.env.pos.payment_methods, function (method) {
                            return method.is_cash_count;
                        });
                        $('.input_percentage_split').each(function( index ) {
                            var nominal_p = parseFloat($( this ).val())
                            if(nominal_p>0){
                                order.add_paymentline(cash_method);
                                var roundedPaymentLine = order.selected_paymentline;
                                roundedPaymentLine.set_amount((nominal_p/100)*total_order);
                            }
                                
                        });

                        this.showScreen('PaymentScreen');
                    }
                    else if (page_active_name.indexOf("Split By Total Amount") >= 0){
                        order.paymentlines.models.forEach(function (p) {
                            order.remove_paymentline(p)
                            
                        });

                        var total_order = order.get_total_with_tax()
                        var total_pay = 0
                        $('.input_amount_split').each(function( index ) {
                            total_pay+=parseFloat($( this ).val())
                        });
                        if (total_order!=total_pay){
                            return this.showPopup('ErrorPopup', {
                                title: this.env._t('Warning !'),
                                body: this.env._t('Please input total split payment same with total order ('+this.env.pos.format_currency(order.get_total_with_tax(),false,currency)+')')
                            })
                        }
                            
                        
                        var cash_method = _.find(this.env.pos.payment_methods, function (method) {
                            return method.is_cash_count;
                        });
                        $('.input_amount_split').each(function( index ) {
                            if(parseFloat($( this ).val())>0){
                                order.add_paymentline(cash_method);
                                var roundedPaymentLine = order.selected_paymentline;
                                roundedPaymentLine.set_amount(parseFloat($( this ).val()));
                            }
                                
                        });

                        this.showScreen('PaymentScreen');
                    }
                    else if (page_active_name.indexOf("Split Per Pax") >= 0){
                        order.paymentlines.models.forEach(function (p) {
                            order.remove_paymentline(p)
                            
                        });
                        var value_person = parseInt($('input#number_person_split').val())
                        var total_order = order.get_total_with_tax()
                        var splitamount = total_order/value_person
                        var cash_method = _.find(this.env.pos.payment_methods, function (method) {
                            return method.is_cash_count;
                        });
                        for (var i = 0; i < value_person; i++) {
                            order.add_paymentline(cash_method);
                            var roundedPaymentLine = order.selected_paymentline;
                            roundedPaymentLine.set_amount(splitamount);
                        }
                        
                        this.showScreen('PaymentScreen');
                    }
                    else if (page_active_name.indexOf("Split By Item") >= 0){
                        if (_.isEmpty(this.splitlines))
                            // Splitlines is empty
                        return;
                        
                        var checkmarkdone = false
                        for (var linedata in order.get_orderlines()) {
                            
                            var dl = order.get_orderlines()[linedata]
                            if (dl.id in this.splitlines){
                                if(this.splitlines[dl.id].checkmark) {
                                    checkmarkdone = true
                                    this._splitQuantity(dl);
                                }
                                else{
                                    this.splitlines[dl.id].quantity = 0
                                }
                                this._updateNewOrder(dl);
                            }
                            else{
                                continue;
                            }
                                
                                
                        }
                        if(!checkmarkdone) {
                            return this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: this.env._t('Please select minimum 1 line for split')
                            })
                        }
                        this._isFinal = true;
                        delete this.newOrder.temporary;

                        if (this._isFullPayOrder()) {
                            this.showScreen('PaymentScreen');
                        } else {
                            this._setQuantityOnCurrentOrder();

                            this.newOrder.set_screen_data({ name: 'PaymentScreen' });

                            // for the kitchen printer we assume that everything
                            // has already been sent to the kitchen before splitting
                            // the bill. So we save all changes both for the old
                            // order and for the new one. This is not entirely correct
                            // but avoids flooding the kitchen with unnecessary orders.
                            // Not sure what to do in this case.

                            if (this.newOrder.saveChanges) {
                                this.currentOrder.saveChanges();
                                this.newOrder.saveChanges();
                            }

                            this.newOrder.set_customer_count(1);
                            const newCustomerCount = this.currentOrder.get_customer_count() - 1;
                            this.currentOrder.set_customer_count(newCustomerCount || 1);
                            this.currentOrder.set_screen_data({ name: 'ProductScreen' });

                            this.env.pos.get('orders').add(this.newOrder);
                            this.env.pos.set('selectedOrder', this.newOrder);
                        }
                    }
                } 
                else {
                    this._isFinal = true;
                    delete this.newOrder.temporary;

                    // if (this._isFullPayOrder()) {
                    this.showScreen('PaymentScreen');
                    // } 
                }
                //     else {
                //         this._setQuantityOnCurrentOrder();

                //         this.newOrder.set_screen_data({name: 'PaymentScreen'});
                //         //
                //         if (this.newOrder.saveChanges) {
                //             this.currentOrder.orderlines.each(function (line) {
                //                 line.set_dirty(false);
                //             });
                //             this.currentOrder.saved_resume = this.currentOrder.build_line_resume();
                //             this.currentOrder.trigger('change', this.currentOrder);

                //             this.newOrder.orderlines.each(function (line) {
                //                 line.set_dirty(false);
                //             });
                //             this.newOrder.saved_resume = this.newOrder.build_line_resume();
                //             this.newOrder.trigger('change', this.newOrder);
                //         }

                //         this.newOrder.set_customer_count(1);
                //         const newCustomerCount = this.currentOrder.get_customer_count() - 1;
                //         this.currentOrder.set_customer_count(newCustomerCount || 1);
                //         this.currentOrder.set_screen_data({name: 'ProductScreen'});

                //         this.env.pos.get('orders').add(this.newOrder);
                //         this.env.pos.set('selectedOrder', this.newOrder);
                //     }
                // }
            }

            async doTransferTable() {
                var oldOrder = this.currentOrder;
                let lists = this.env.pos.tables.filter((t) => t.id != oldOrder.table.id).map((t) => ({
                    id: t.id,
                    item: t,
                    label: t.floor.name + ' / ' + t.name
                }))
                let {confirmed, payload: table} = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Alert, please select table need moving Lines just selected'),
                    list: lists
                })
                if (confirmed) {
                    if (_.isEmpty(this.splitlines))
                        // Splitlines is empty
                        return;
                    this._isFinal = true;
                    this.transferLines(table)
                    delete this.newOrder.temporary;
                }
            }

            getTableOrdered(table_id) {
                var orders = this.env.pos.get('orders').models
                for (var i = 0; i < orders.length; i++) {
                    var order = orders[i];
                    if (order.table && order.table.id == table_id) {
                        return order
                    }
                }
                return null;
            }

            async transferLines(table) {
                // todo: currentOrder (1) has selected split, newOrder is split from (1), toOrder: is order transfer clone lines selected
                // case 1: line has send receipt to kitchen ==> auto set selectedOrder to saveChanges()
                // case 2: line not send to kitchen
                var oldOrder = this.currentOrder;
                var ordered = this.getTableOrdered(table.id);
                let lineMoves = [];
                for (let id in this.splitlines) {
                    if (this.splitlines[id].quantity > 0) {
                        lineMoves.push(this.splitlines[id])
                    }
                }
                if (lineMoves.length == 0) {
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('Please select minimum 1 line of Order Lines')
                    })
                }
                let toOrder = null;
                if (ordered == null) {
                    toOrder = new models.Order({}, {
                        pos: this.env.pos,
                    });
                    toOrder.table = table;
                    this.env.pos.get('orders').add(toOrder);
                } else {
                    toOrder = ordered;
                }
                for (let line_id in this.splitlines) {
                    let liveMove = this.newOrderLines[line_id];
                    let qtyMove = this.splitlines[line_id].quantity;
                    if (this.splitlines[line_id].quantity > 0) {
                        let newLine = liveMove.clone();
                        toOrder.add_orderline(newLine);
                        newLine.set_quantity(qtyMove)
                        let lineWillUpdate = oldOrder.get_orderline(parseInt(line_id));
                        if (lineWillUpdate.quantity == qtyMove) {
                            oldOrder.remove_orderline(lineWillUpdate);
                        } else {
                            lineWillUpdate.set_quantity(lineWillUpdate.quantity - qtyMove, 'do not recompute unit price')
                        }
                        newLine.mp_dirty = lineWillUpdate.mp_dirty
                        newLine.mp_skip = lineWillUpdate.mp_skip
                        // Case 1: saveChanges if line transfer done send receipt to kitchen
                        if (!newLine.mp_dirty) {
                            toOrder.saveChanges()
                        }
                        newLine.trigger('change', newLine);
                    }
                }
                toOrder.trigger('change', toOrder);
                toOrder.set_screen_data({name: 'ProductScreen'});
                posbus.trigger('reset-screen');
                if (toOrder.hasChangesToPrint()) {
                    const isPrintSuccessful = await toOrder.printChanges();
                    if (isPrintSuccessful) {
                        toOrder.saveChanges();
                    }
                }
                oldOrder.set_screen_data({name: 'ProductScreen'});
                if (oldOrder.orderlines.length == 0) {
                    oldOrder.finalize()
                }
                this.env.pos.set('selectedOrder', toOrder);
            }

        }
    Registries.Component.extend(SplitBillScreen, RetailSplitBillScreen);

    return RetailSplitBillScreen;
});
