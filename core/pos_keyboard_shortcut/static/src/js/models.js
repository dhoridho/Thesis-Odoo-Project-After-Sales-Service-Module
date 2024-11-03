odoo.define('point_of_sale.pos_keyboard_shortcut', function(require) {
    'use strict';
    const { Component } = owl;
    const { EventBus } = owl.core;
    const { onMounted, onWillUnmount, useExternalListener } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const { parse } = require('web.field_utils');
    const { BarcodeEvents } = require('barcodes.BarcodeEvents');
    const { _t } = require('web.core');
    const INPUT_KEYS = new Set(
        ['Delete', 'Backspace', '+1', '+2', '+5', '+10', '+20', '+50'].concat('0123456789+-.,'.split(''))
    );
    const CONTROL_KEYS = new Set(['Esc']);
    const ALLOWED_KEYS = new Set([...INPUT_KEYS, ...CONTROL_KEYS]);
    const getDefaultConfig = () => ({
        decimalPoint: false,
        triggerAtEnter: false,
        triggerAtEsc: false,
        triggerAtInput: false,
        nonKeyboardInputEvent: false,
        useWithBarcode: false,
    });
    var fired = false;

    /**
     * @prop {'quantiy' | 'price' | 'discount'} activeMode
     * @event set-numpad-mode - triggered when mode button is clicked
     * @event numpad-click-input - triggered when numpad button is clicked
     *
     * IMPROVEMENT: Whenever new-orderline-selected is triggered,
     * numpad mode should be set to 'quantity'. Now that the mode state
     * is lifted to the parent component, this improvement can be done in
     * the parent component.
     */

    class NumberKeyboardBuffer extends EventBus {
        constructor() {
            super();
            this.isReset = false;
            this.bufferHolderStack = [];
        }
        /**
         * @returns {String} value of the buffer, e.g. '-95.79'
         */
        get() {
            return this.state ? this.state.buffer : null;
        }
        /**
         * Takes a string that is convertible to float, and set it as
         * value of the buffer. e.g. val = '2.99';
         *
         * @param {String} val
         */
        set(val) {
            this.state.buffer = !isNaN(parseFloat(val)) ? val : '';
            this.trigger('buffer-update', this.state.buffer);
        }
        /**
         * Resets the buffer to empty string.
         */
        reset() {
            this.isReset = true;
            this.state.buffer = '';
            this.trigger('buffer-update', this.state.buffer);
        }
        capture() {
            if (this.handler) {
                clearTimeout(this._timeout);
                this.handler();
                delete this.handler;
            }
        }
        /**
         * @returns {number} float equivalent of the value of buffer
         */
        getFloat() {
            return parse.float(this.get());
        }
        activate() {
            this.defaultDecimalPoint = _t.database.parameters.decimal_point;
            useExternalListener(window, 'keyup', this._onKeyboardShortcutInput.bind(this));
        }
        /**
         * @param {Object} config Use to setup the buffer
         * @param {String|null} config.decimalPoint The decimal character.
         * @param {String|null} config.triggerAtEnter Event triggered when 'Enter' key is pressed.
         * @param {String|null} config.triggerAtEsc Event triggered when 'Esc' key is pressed.
         * @param {String|null} config.triggerAtInput Event triggered for every accepted input.
         * @param {String|null} config.nonKeyboardInputEvent Also listen to a non-keyboard input event
         *      that carries a payload of { key }. The key is checked if it is a valid input. If valid,
         *      the number buffer is modified just as it is modified when a keyboard key is pressed.
         * @param {Boolean} config.useWithBarcode Whether this buffer is used with barcode.
         * @emits config.triggerAtEnter when 'Enter' key is pressed.
         * @emits config.triggerAtEsc when 'Esc' key is pressed.
         * @emits config.triggerAtInput when an input is accepted.
         */
        use(config) {
            this.eventsBuffer = [];
            const currentComponent = Component.current;
            config = Object.assign(getDefaultConfig(), config);
            onMounted(() => {
                this.bufferHolderStack.push({
                    component: currentComponent,
                    state: config.state ? config.state : { buffer: '' },
                    config,
                });
                this._setUp();
            });
            onWillUnmount(() => {
                this.bufferHolderStack.pop();
                this._setUp();
            });
            // Add listener that accepts non keyboard inputs
            if (typeof config.nonKeyboardInputEvent === 'string') {
                useListener(config.nonKeyboardInputEvent, this._onNonKeyboardShortcutInput.bind(this));
            }
        }
        get _currentBufferHolder() {
            return this.bufferHolderStack[this.bufferHolderStack.length - 1];
        }
        _setUp() {
            if (!this._currentBufferHolder) return;
            const { component, state, config } = this._currentBufferHolder;
            this.component = component;
            this.state = state;
            this.config = config;
            this.decimalPoint = config.decimalPoint || this.defaultDecimalPoint;
            this.maxTimeBetweenKeys = this.config.useWithBarcode
                ? BarcodeEvents.max_time_between_keys_in_ms
                : 0;
        }
        _onKeyboardShortcutInput(event) {
            return this._bufferEvents(this._onInput(event => event.key))(event);
        }
        _onNonKeyboardShortcutInput(event) {
            return this._bufferEvents(this._onInput(event => event.detail.key))(event);
        }
        _bufferEvents(handler) {
            return event => {
                if (['INPUT', 'TEXTAREA'].includes(event.target.tagName) || !this.eventsBuffer) return;
                clearTimeout(this._timeout);
                this.eventsBuffer.push(event);
                this._timeout = setTimeout(handler, this.maxTimeBetweenKeys);
                this.handler = handler
            };
        }
        _onInput(keyAccessor) {
            return () => {
                if (this.eventsBuffer.length <= 2) {
                    // Check first the buffer if its contents are all valid
                    // number input.
                    for (let event of this.eventsBuffer) {
                        if (!ALLOWED_KEYS.has(keyAccessor(event))) {
                            this.eventsBuffer = [];
                            this.perform_event(event);
                            return;
                        }
                    }
                    // At this point, all the events in buffer
                    // contains number input. It's now okay to handle
                    // each input.
                    for (let event of this.eventsBuffer) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                }
                this.eventsBuffer = [];
            };
        }
        scroll_cashier(shortcut_pressed){
            if(shortcut_pressed == 'ARROWDOWN'){
                if($('.selection-item').hasClass('selected')){
                    var current = $('.selection-item.selected')
                    if(current.next().hasClass('selection-item')){
                        current.next().addClass('selected');
                        current.removeClass('selected');
                        var index = $('.selection-item.selected').index();
                        $('.selection.scrollable-y').animate({
                            scrollTop: 50*index
                        },50);
                    }
                    else{
                        current.removeClass('selected')
                        $('.selection.scrollable-y div:first-child').addClass('selected')
                        $('.selection.scrollable-y').animate({
                            scrollTop: 0
                        },50);
                    }
                }
                else
                    $('.selection.scrollable-y div:first-child').addClass('selected')
            }
            if(shortcut_pressed == 'ARROWUP'){
                if($('.selection-item').hasClass('selected')){
                    var current = $('.selection-item.selected')
                    if(current.prev().hasClass('selection-item')){
                        current.prev().addClass('selected');
                        current.removeClass('selected');
                        var index = $('.selection-item.selected').index();
                        $('.selection.scrollable-y').animate({
                            scrollTop: 50*index
                        },50);
                    } else {
                        current.removeClass('selected')
                        $('.selection.scrollable-y div:last-child').addClass('selected')
                        var index = $('.selection-item.selected').index();
                        $('.selection.scrollable-y').animate({
                            scrollTop: 50*index
                        },50);
                    }
                }
                else
                    $('.selection.scrollable-y div:first-child').addClass('selected')
            }
        }
        remove_classes(){
            $('.actionpad button:nth-child(1)').removeClass('overlay')
            $('.button.set-customer').removeClass('overlay')
            $('.button.pay').removeClass('overlay')
            $("button.mode-button:contains(Qty)").removeClass('overlay');
            $("button.mode-button:contains(Disc)").removeClass('overlay');
            $("button.mode-button:contains(Price)").removeClass('overlay');
            $('.username').removeClass('overlay')
            $('.button.new-customer').removeClass('overlay')
            $('.button.back').removeClass('overlay')
            $(".button.paymentmethod").removeClass('overlay')
            $('.button.print').removeClass('overlay');
            $("div.status-buttons div:nth-child(3)").removeClass('overlay')
            $('.header-button.close_button').removeClass('overlay')
            $(".ticket-button").removeClass('overlay')
            $('.hidden_tags').hide();
            $('.hidden_tags_header').hide();
            $('.button.back').removeClass('overlay');
            $(".button.print").removeClass('overlay');
            $(".button.next").removeClass('overlay');
            $(".button.js_invoice").removeClass('overlay');
            $(".customer-button .button").removeClass('overlay');
            $(".button.next").removeClass('overlay');
            return false
        }
        perform_event(e){
            var self = this;
            if(self.component.env.pos.config.enable_shortcuts){
                var product_screen = $(".product-screen.screen").is(':visible');
                var payment_screen = $(".payment-screen.screen").is(':visible');
                var clientlist_screen = $(".clientlist-screen.screen").is(':visible');
                var receipt_screen = $(".receipt-screen.screen").is(':visible');
                var ticket_screen = $(".ticket-screen.screen").is(':visible');
                
                var shortcut_pressed = e.key.toUpperCase();
                var all_shortcuts = self.component.env.pos.db.shortcuts_by_id[self.component.env.pos.config.select_shortcut[0]];
    
                if (product_screen){
                    var is_popup = $("div.popups").is(":visible")
                    if(e.keyCode == 17){
                        if(fired){
                            fired = false;
                            self.remove_classes();
                        } else {  
                            fired = true;
                            var all_shortcuts = self.component.env.pos.db.shortcuts_by_id[self.component.env.pos.config.select_shortcut[0]];
                            if(all_shortcuts.customer_screen){
                                $('.button.set-customer span').html(all_shortcuts.customer_screen.toUpperCase())
                                $('.button.set-customer').addClass('overlay');
                            }
                            if(all_shortcuts.next_screen){
                                $('.button.pay span:last-child').html(all_shortcuts.next_screen.toUpperCase())                                   
                                $('.button.pay').addClass('overlay');                                                                         
                            }
                            if(all_shortcuts.select_qty){
                                $("button.mode-button:contains(Qty) span").html(all_shortcuts.select_qty.toUpperCase())
                                $("button.mode-button:contains(Qty)").addClass('overlay');
                            }
                            if(all_shortcuts.select_discount){
                                $("button.mode-button:contains(Disc) span").html(all_shortcuts.select_discount.toUpperCase())
                                $("button.mode-button:contains(Disc)").addClass('overlay');               
                            }
                            if(all_shortcuts.select_price){
                                $("button.mode-button:contains(Price) span").html(all_shortcuts.select_price.toUpperCase())
                                $("button.mode-button:contains(Price)").addClass('overlay');
                            }
                            if(all_shortcuts.select_user){
                                $('span.username span').html(all_shortcuts.select_user.toUpperCase());
                                $('span.username').addClass('overlay')
                            }
                            if(all_shortcuts.refresh){
                                $("div.status-buttons div:nth-child(3) span").html(all_shortcuts.refresh.toUpperCase());
                                $("div.status-buttons div:nth-child(3)").addClass('overlay')
                            }
                            if(all_shortcuts.see_all_order){
                                $(".ticket-button div:nth-child(2) span").html(all_shortcuts.see_all_order.toUpperCase());
                                $(".ticket-button").addClass('overlay')
                            }
                            if($('.header-button.close_button').length){
                                if(all_shortcuts.close_pos){
                                    $('.header-button.close_button span').html(all_shortcuts.close_pos.toUpperCase());
                                    $('.header-button.close_button').addClass('overlay')
                                }
                            }
                            $('.hidden_tags').show();
                            $('.hidden_tags_header').show();
                        }
                    }
    
                    if(!is_popup){
                        if(all_shortcuts.next_screen && (shortcut_pressed == all_shortcuts.next_screen.toUpperCase())){
                            e.preventDefault();
                            $('.button.pay').click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.customer_screen && (shortcut_pressed == all_shortcuts.customer_screen.toUpperCase())){
                            e.preventDefault();
                            $('.button.set-customer').click();
                            setTimeout(function(){
                                $('.searchbox-client input').focus();
                            },50);
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.create_customer && (shortcut_pressed == all_shortcuts.create_customer.toUpperCase())){
                            e.preventDefault();
                            $('.button.set-customer').click();
                            setTimeout(function(){
                                $('.button.new-customer').click();
                                setTimeout(function(){
                                    $('.detail.client-name').focus();
                                },100);
                            },100);
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.search_product && (shortcut_pressed == all_shortcuts.search_product.toUpperCase())){
                            e.preventDefault();
                            $('.search-box input').focus();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.select_qty && (shortcut_pressed == all_shortcuts.select_qty.toUpperCase())){
                            e.preventDefault();
                            $("button.mode-button:contains(Qty)").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.select_discount && (shortcut_pressed == all_shortcuts.select_discount.toUpperCase())){
                            e.preventDefault();
                            $("button.mode-button:contains(Disc)").click();
                            fired = self.remove_classes();
                        }    
                        if(all_shortcuts.select_price && (shortcut_pressed == all_shortcuts.select_price.toUpperCase())){
                            e.preventDefault();
                            $("button.mode-button:contains(Price)").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.see_all_order && (shortcut_pressed == all_shortcuts.see_all_order.toUpperCase())){
                            e.preventDefault();
                            $("div.ticket-button").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.select_user && (shortcut_pressed == all_shortcuts.select_user.toUpperCase())){
                            e.preventDefault();
                            $("span.username").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.refresh && (shortcut_pressed == all_shortcuts.refresh.toUpperCase())){
                            e.preventDefault();
                            $("div.status-buttons div:nth-child(3)").click();
                            fired = self.remove_classes();
                        }
                        if($('.header-button.close_button').length){
                            if(all_shortcuts.close_pos && (shortcut_pressed == all_shortcuts.close_pos.toUpperCase())){
                                e.preventDefault();
                                $(".header-button.close_button").click();
                                fired = self.remove_classes();
                            }
                        }
                        if($('.product-list article').is(':focus')){
                            if(e.key.toUpperCase() == all_shortcuts.navigate_product_right.toUpperCase()){
                                if(document.activeElement.nextSibling && document.activeElement.nextSibling.className == 'product')
                                    document.activeElement.nextSibling.focus();
                                else
                                    $('.product-list article:first-child').focus();
                            }
                            if(e.key.toUpperCase() == all_shortcuts.navigate_product_left.toUpperCase()){
                                if(document.activeElement.previousSibling && document.activeElement.previousSibling.className == 'product')
                                    document.activeElement.previousSibling.focus();
                                else
                                    $('.product-list article:last-child').focus();
                            }
                            if(e.key.toUpperCase() == 'ARROWUP' || e.key.toUpperCase() == 'ARROWDOWN'){
                                $( "div .product-list article:focus" ).blur()
                                $(".orderline.selected").focus()
                            }
                            if(e.key.toUpperCase() == 'ENTER'){
                                if($(".product").is(":focus")){
                                    if(e.keyCode == 13 && document.activeElement && (document.activeElement.className == 'product')){
                                        let product_id = document.activeElement.getAttribute('data-product-id');
                                        $("[data-product-id~='"+product_id+"']").click();
                                        $("[data-product-id~='"+product_id+"']").focus();
                                    }
                                }
                            }
                            fired = self.remove_classes();
                        }
                        if(!$('.product-list article').is(':focus')){
                            if(e.key.toUpperCase() == 'ARROWUP'){
                                if($('li.orderline.selected').length){
                                    $('li.orderline.selected').prev().click();
                                    if($('li.orderline.selected').prev().length){
                                        $('.product-screen.screen .order-container').animate({
                                            scrollTop: $('li.orderline.selected').offset().top - $('.product-screen.screen .order-container').offset().top - $('.product-screen.screen .order-container').offset().top - $('.product-screen.screen .order-container').offset().top + $('.product-screen.screen .order-container').scrollTop()
                                        },50);
                                    }
                                }
                            }
                            if(e.key.toUpperCase() == 'ARROWDOWN'){
                                if($('li.orderline.selected').length){
                                    $('li.orderline.selected').next().click();
                                    if($('li.orderline.selected').next().length){
                                        $('.product-screen.screen .order-container').animate({
                                            scrollTop: $('li.orderline.selected').offset().top - $('.product-screen.screen .order-container').offset().top + $('.product-screen.screen .order-container').scrollTop()
                                        },50);
                                    }
                                }
                            }
                            if(e.key.toUpperCase() == 'ARROWLEFT' || e.key.toUpperCase() == 'ARROWRIGHT'){
                                $( "div .product-list article:first-child" ).focus()
                                $(".orderline.selected").blur()
                            }
                            fired = self.remove_classes();
                        }
                    } else {
                        // Employee Selection
                        if(shortcut_pressed == 'ARROWDOWN'){
                            self.scroll_cashier(shortcut_pressed);
                        }
                        if(shortcut_pressed == 'ARROWUP'){
                            self.scroll_cashier(shortcut_pressed);
                        }
                        if(shortcut_pressed == 'ENTER'){
                            $('.button.confirm').click();
                        }
                    }
                }
                else if(ticket_screen){
                    var is_popup = $("div.popups").is(":visible")
                    if(!is_popup){
                        if(all_shortcuts.back_screen && (shortcut_pressed == all_shortcuts.back_screen.toUpperCase())){
                            e.preventDefault();
                            $('button.discard').click();
                        }
                        if(all_shortcuts.search_product && (shortcut_pressed == all_shortcuts.search_product.toUpperCase())){
                            e.preventDefault();
                            $('.search input').focus();
                        }
                    }
                    else{
                        if(shortcut_pressed == 'ENTER'){
                            $('.button.confirm').click();
                        }
    
                    }
                }
                else if(clientlist_screen){
                    var is_popup = $("div.popups").is(":visible")
                    if(e.keyCode == 17){
                        if(fired){
                            fired = false;
                            self.remove_classes();
                        }
                        else{  
                            fired = true;
                            var all_shortcuts = self.component.env.pos.db.shortcuts_by_id[self.component.env.pos.config.select_shortcut[0]];
                            if(all_shortcuts.back_screen){
                                $(".button.back span").html(all_shortcuts.back_screen.toUpperCase());
                                $(".button.back").addClass('overlay')
                            }
                            if(all_shortcuts.create_customer){
                                $(".button.new-customer span").html(all_shortcuts.create_customer.toUpperCase());
                                $(".button.new-customer").addClass('overlay')
                            }
                            $('.hidden_tags').show();
                            $('.hidden_tags_header').show();
                        }
                    }
                    if(!is_popup){
                        if(all_shortcuts.back_screen && (shortcut_pressed == all_shortcuts.back_screen.toUpperCase())){
                            e.preventDefault();
                            $('.button.back').click();
                        }
                        if(all_shortcuts.search_product && (shortcut_pressed == all_shortcuts.search_product.toUpperCase())){
                            e.preventDefault();
                            $('.searchbox-client input').focus();
                        }
                        if(all_shortcuts.create_customer && (shortcut_pressed == all_shortcuts.create_customer.toUpperCase())){
                            e.preventDefault();
                            $('.button.new-customer').click();
                            fired = self.remove_classes();
                        }
                        if(e.key.toUpperCase() == 'ARROWDOWN'){
                            if($('.client-list .client-list-contents .highlight').length){
                                $('.client-list .client-list-contents .highlight').next().click();
                                if($('.client-list .client-list-contents .highlight').offset() && $('.subwindow-container-fix.touch-scrollable.scrollable-y').offset()){
                                    $('.subwindow-container-fix.touch-scrollable.scrollable-y').animate({
                                        scrollTop: $('.client-list .client-list-contents .highlight').offset().top - $('.subwindow-container-fix.touch-scrollable.scrollable-y').offset().top + $('.subwindow-container-fix.touch-scrollable.scrollable-y').scrollTop()
                                    },50);
                                }
                            }
                            else
                                $('.client-list .client-list-contents tr:first-child').click()
                        }
                        if(e.key.toUpperCase() == 'ARROWUP'){
                            if($('.client-list .client-list-contents .highlight').length){
                                $('.client-list .client-list-contents .highlight').prev().click();
                                if($('.client-list .client-list-contents .highlight').offset() && $('.subwindow-container-fix.touch-scrollable.scrollable-y').offset()){
                                    $('.subwindow-container-fix.touch-scrollable.scrollable-y').animate({
                                        scrollTop: $('.client-list .client-list-contents .highlight').offset().top - $('.subwindow-container-fix.touch-scrollable.scrollable-y').offset().top + $('.subwindow-container-fix.touch-scrollable.scrollable-y').scrollTop()
                                    },50)
                                }
                            }
                            else
                                $('.client-list .client-list-contents tr:first-child').click()
                        }
                        if(e.key.toUpperCase() == 'ENTER'){
                            if($(".client-line.highlight").is(":visible")){
                                $('.button.next.highlight').click()
                            }
                        }
                    } else {
                        if(shortcut_pressed == 'ENTER'){
                            $('.button.confirm').click();
                        }
                    }
                }
                else if(payment_screen){
                    var is_popup = $("div.popups").is(":visible")
                    // CONTROL_KEYS == 17
                    if(e.keyCode == 17){
                        if(fired){
                            fired = false;
                            self.remove_classes();
                        }
                        else{  
                            fired = true;
                            var all_shortcuts = self.component.env.pos.db.shortcuts_by_id[self.component.env.pos.config.select_shortcut[0]];
                            if(all_shortcuts.select_user){
                                $('span.username span').html(all_shortcuts.select_user.toUpperCase());
                                $('span.username').addClass('overlay')
                            }
                            if(all_shortcuts.refresh){
                                $("div.status-buttons div:nth-child(3) span").html(all_shortcuts.refresh.toUpperCase());
                                $("div.status-buttons div:nth-child(3)").addClass('overlay')
                            }
                            if(all_shortcuts.see_all_order){
                                $(".ticket-button div:nth-child(2) span").html(all_shortcuts.see_all_order.toUpperCase());
                                $(".ticket-button").addClass('overlay')
                            }
                            if($('.header-button.close_button').length){
                                if(all_shortcuts.close_pos){
                                    $('.header-button.close_button span').html(all_shortcuts.close_pos.toUpperCase());
                                    $('.header-button.close_button').addClass('overlay')
                                }
                            }
                            if(all_shortcuts.back_screen){
                                $(".button.back span.hidden_tags").html(all_shortcuts.back_screen.toUpperCase());
                                $(".button.back").addClass('overlay')
                            }
                            if(all_shortcuts.order_invoice){
                                $(".button.js_invoice span.hidden_tags").html(all_shortcuts.order_invoice.toUpperCase());
                                $(".button.js_invoice").addClass('overlay')
                            }
                            if(all_shortcuts.customer_screen){
                                $(".customer-button .button span.hidden_tags").html(all_shortcuts.customer_screen.toUpperCase());
                                $(".customer-button .button").addClass('overlay')
                            }
                            if ($(".button.next").is(':visible')){
                                $(".button.next span.hidden_tags").html('ENTER');
                                $(".button.next").addClass('overlay')
                            }
                            var journal_key_shortcuts = []
                            _.each(self.component.env.pos.journal_key,function(value){
                                var dict_values = {
                                    'id'  : value.payment_method_id[0],
                                    'key' : value.key_journals,
                                }
                                journal_key_shortcuts.push(dict_values);
                            });
                            _.each(journal_key_shortcuts, function(value){
                                if(value.key){
                                    $("[data-payment-id~='"+value.id+"']").siblings('.hidden_tags').html(value.key)
                                    $("[data-payment-id~='"+value.id+"']").parent().addClass('overlay')
                                }
                            });
                            $('.hidden_tags').show();
                            $('.hidden_tags_header').show();
                        }
                    }
                    if(!is_popup){
                        if(all_shortcuts.back_screen && (shortcut_pressed == all_shortcuts.back_screen.toUpperCase())){
                            e.preventDefault();
                            $('.button.back').click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.customer_screen && (shortcut_pressed ==  all_shortcuts.customer_screen.toUpperCase())){
                            e.preventDefault();
                            $('.customer-button .button').click();
                            setTimeout(function(){
                                $('.searchbox-client input').focus();
                                fired = self.remove_classes();
                            },50);                       
                        }
                        if(all_shortcuts.order_invoice && (shortcut_pressed == all_shortcuts.order_invoice.toUpperCase())){
                            e.preventDefault();
                            $('.button.js_invoice').click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.see_all_order && (shortcut_pressed == all_shortcuts.see_all_order.toUpperCase())){
                            e.preventDefault();
                            $("div.ticket-button").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.select_user && (shortcut_pressed == all_shortcuts.select_user.toUpperCase())){
                            e.preventDefault();
                            $("span.username").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.refresh && (shortcut_pressed == all_shortcuts.refresh.toUpperCase())){
                            e.preventDefault();
                            $("div.status-buttons div:nth-child(3)").click();
                            fired = self.remove_classes();
                        }
                        if($('.header-button.close_button').length){
                            if(all_shortcuts.close_pos && (shortcut_pressed == all_shortcuts.close_pos.toUpperCase())){
                                e.preventDefault();
                                $(".header-button.close_button").click();
                                fired = self.remove_classes();
                            }
                        }
                        if(e.key.toUpperCase() == 'ENTER'){
                            if($(".button.next").is(":visible")){
                                $('.button.next').click()
                            }
                            fired = self.remove_classes();
                        }
                        var journal_key_shortcuts = []
                        _.each(self.component.env.pos.journal_key,function(value){
                            var dict_values = {
                                'id'  : value.payment_method_id[0],
                                'key' : value.key_journals,
                            }
                            journal_key_shortcuts.push(dict_values);
                        });
                        _.each(journal_key_shortcuts, function(value){
                            if(value.key && (value.key.toUpperCase() == shortcut_pressed)){
                                fired = self.remove_classes();
                                self.click_paymentmethods(value.id);
                            }
                        });
                    } else {
                        // Employee Selection
                        if(shortcut_pressed == 'ARROWDOWN'){
                            self.scroll_cashier(shortcut_pressed);
                        }
                        if(shortcut_pressed == 'ARROWUP'){
                            self.scroll_cashier(shortcut_pressed);
                        }
                        if(shortcut_pressed == 'ENTER'){
                            $('.button.confirm').click();
                        }
                    }
                }
                else if(receipt_screen){
                    var is_popup = $("div.popups").is(":visible")
                    if(e.keyCode == 17){
                        if(fired){
                            fired = false;
                            self.remove_classes();
                        } else {  
                            fired = true;
                            var all_shortcuts = self.component.env.pos.db.shortcuts_by_id[self.component.env.pos.config.select_shortcut[0]];
                            if(all_shortcuts.select_user){
                                $('span.username span').html(all_shortcuts.select_user.toUpperCase());
                                $('span.username').addClass('overlay')
                            }
                            if(all_shortcuts.refresh){
                                $("div.status-buttons div:nth-child(3) span").html(all_shortcuts.refresh.toUpperCase());
                                $("div.status-buttons div:nth-child(3)").addClass('overlay')
                            }
                            if(all_shortcuts.see_all_order){
                                $(".ticket-button div:nth-child(2) span").html(all_shortcuts.see_all_order.toUpperCase());
                                $(".ticket-button").addClass('overlay')
                            }
                            if($('.header-button.close_button').length){
                                if(all_shortcuts.close_pos){
                                    $('.header-button.close_button span').html(all_shortcuts.close_pos.toUpperCase());
                                    $('.header-button.close_button').addClass('overlay')
                                }
                            }
                            if(all_shortcuts.back_screen){
                                $(".button.back span.hidden_tags").html(all_shortcuts.back_screen.toUpperCase());
                                $(".button.back").addClass('overlay')
                            }
    
                            if(all_shortcuts.print_receipt){
                                $(".button.print span.hidden_tags").html(all_shortcuts.print_receipt.toUpperCase());
                                $(".button.print").addClass('overlay')
                            }
                            if(all_shortcuts.next_screen_show){
                                $(".button.next span.hidden_tags").html(all_shortcuts.next_screen_show.toUpperCase());
                                $(".button.next").addClass('overlay')
                            }
                            $('.hidden_tags').show();
                            $('.hidden_tags_header').show();
                        }
                    }
                    if(!is_popup){
                        if(all_shortcuts.next_screen_show && (shortcut_pressed == all_shortcuts.next_screen_show.toUpperCase())){
                            e.preventDefault();
                            $(".button.next").click();
                            fired = self.remove_classes();
                        }
                        if(all_shortcuts.print_receipt && (shortcut_pressed == all_shortcuts.print_receipt.toUpperCase())){
                            e.preventDefault();
                            $(".button.print").click();
                            fired = self.remove_classes();
                        }
                    } else {
                        if(shortcut_pressed == 'ENTER'){
                            $('.button.confirm').click();
                        }
                    }
                } else {
                    var is_popup = $("div.popups").is(":visible")
                    if(e.keyCode == 17){
                        if(fired){
                            fired = false;
                            self.remove_classes();
                        } else {  
                            fired = true;
                            var all_shortcuts = self.component.env.pos.db.shortcuts_by_id[self.component.env.pos.config.select_shortcut[0]];
                            if(all_shortcuts.back_screen){
                                $(".button.back span.hidden_tags").html(all_shortcuts.back_screen.toUpperCase());
                                $(".button.back").addClass('overlay')
                            }
                            $('.hidden_tags').show();
                            $('.hidden_tags_header').show();
                        }
                    }
                    if(!is_popup){
                        if(all_shortcuts.back_screen && (shortcut_pressed == all_shortcuts.back_screen.toUpperCase())){
                            e.preventDefault();
                            $('.button.back').click();
                            fired = self.remove_classes();
                        }
                    } else {
                        if(shortcut_pressed == 'ENTER'){
                            $('.button.confirm').click();
                        }
                    }
                }
            }
        }
        click_paymentmethods(payment_id){
            $("[data-payment-id~='"+payment_id+"']").parent().click()
        }
    }
    return new NumberKeyboardBuffer();
});
