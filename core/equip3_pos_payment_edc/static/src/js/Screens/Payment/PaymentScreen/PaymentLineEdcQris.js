odoo.define('equip3_pos_payment_edc.PaymentLineEdcQris', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');

    const core = require('web.core');
    const _t = core._t;
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');
    const qweb = core.qweb;
    const framework = require('web.framework');

    let countdownEDC = 90; //seconds
    let timer = null;
    let timerCounterPrintedStatus = null;
    let timerCounterCheckPayment = null;

    class PaymentLineEdcQris extends PosComponent {
        constructor() {
            super(...arguments);
        }

        getApprovalCode(paymentline){
            return paymentline.approval_code;
        }

        async sendRequestQris(paymentline) {
            console.log('EDC Qris: Send Request...')
            const self = this
            const order = this.env.pos.get_order()
            let payment_edc_date = moment().format('YYYYMMDD-hhmmss');
            let order_number = order.uid + '-D-' + payment_edc_date;
            let payment = paymentline.payment_method;

            if(payment){
                let payment_display = self.env.pos.format_currency(order.get_total_with_tax());
                let order_amount = parseInt(order.get_total_with_tax() + '00')
                let trant_amount = order_amount.toLocaleString('en-US', {minimumIntegerDigits: 12, useGrouping:false})

                let url = '#edc-payment-qris';
                if (payment.is_edc_bca){
                    let port = payment.edc_port.trim();
                    url = 'http://localhost:' + port + '/edc-bca'
                }
                let data = {
                    'data': {
                        'order_number': order_number,
                        'version': '03',
                        'trans_type': '31',
                        'trans_amount': trant_amount,
                        'other_amount': '000000000000',
                        'pan': '1688700627201892   ',
                        'expiry_date': '2510',
                        'cancel_reason': '00',
                        'invoice_number': '',
                        'auth_code': '000000',
                        'installment_flag': '',
                        'redeem_flag': '',
                        'dcc_fllag': 'N',
                        'installment_plan': '000',
                        'installment_tenor': '00',
                        'generic_data': '',
                        'reff_number': '',
                        'original_date': '',
                        'bca_filler': ''
                    }
                }

                self.paymentEdcBlockUi('Connecting to EDC Driver...');
                let result = await self.makeRequestEDC({
                    url: url,
                    data: data,
                });

                if(result.status == 'error'){
                    self.paymentEdcUnblockUi();
                    Gui.showPopup('ErrorPopup', {
                        title: 'Error',
                        body: result.message,
                    });
                    return;
                }

                if(result.status == 'waiting'){
                    self.paymentEdcBlockUi( `Payment amount ${payment_display} is being processed` );
                    self.paymentEdcBlockUiCountdown();
                    let payment = await self.checkPrintedStatus(order_number);
                    console.log('EDC Qris: Printed status: - ' , payment);
                    if(payment.status == 'Expired'){
                        self.paymentEdcUnblockUi();
                        Gui.showPopup('ErrorPopup', {
                            title: payment.status,
                            body: payment.message,
                        });
                        return;
                    }

                    if(!payment.data.rrn){
                        self.paymentEdcUnblockUi();
                        Gui.showPopup('ErrorPopup', {
                            title: 'ERROR',
                            body: 'RRN code is empty!',
                        });
                        return;
                    }

                    if(payment.resp_code != '00'){
                        self.paymentEdcUnblockUi();
                        let error_message = self.getErrorCodeMessage(payment.resp_code);
                        if(!error_message){
                            error_message += '\n\n';
                        }
                        if(!payment.message){
                            error_message += payment.message;
                        }
                        Gui.showPopup('ConfirmPopup', {
                            title: 'Payment Status (' + payment.resp_code + ')',
                            body: error_message,
                        });
                        return;
                    }

                    paymentline.payment_edc_rrn = payment.data.rrn; //reffcode
                    paymentline.payment_edc_state = 'sent';

                    order.is_payment_edc = true;
                    order.payment_edc_id = payment.data.id;
                    self.paymentEdcBlockUi('Successfully Printed QR code');
                    $('.edc-payment-loader-wrap .edc-payment-countdown').hide();

                    self.render();
                    setTimeout(function(){
                        self.paymentEdcUnblockUi();
                    }, 1000);
                }
            }
        } 

        async checkPaymentQris(paymentline) {
            console.log('Check Payment Qris: Payment Status...')
            console.log('Check Payment Qris: paymentline...', paymentline)
            const self = this
            const order = this.env.pos.get_order()
            let payment_edc_date = moment().format('YYYYMMDD-hhmmss');
            let order_number = order.uid + '-D-' + payment_edc_date;
            let payment = paymentline.payment_method;

            if(payment){
                let payment_display = self.env.pos.format_currency(order.get_total_with_tax());
                let order_amount = parseInt(order.get_total_with_tax() + '00')
                let trant_amount = order_amount.toLocaleString('en-US', {minimumIntegerDigits: 12, useGrouping:false})

                let url = '#edc-check-payment-qris';
                if (payment.is_edc_bca){
                    let port = payment.edc_port.trim();
                    url = 'http://localhost:' + port + '/edc-bca'
                }
                let data = {
                    'data': {
                        'order_number': order_number,
                        'version': '03',
                        'trans_type': '32',
                        'trans_amount': '000000000000',
                        'other_amount': '000000000000',
                        'pan': '',
                        'expiry_date': '',
                        'cancel_reason': '00',
                        'invoice_number': '000000',
                        'auth_code': '',
                        'installment_flag': '',
                        'redeem_flag': '',
                        'dcc_fllag': 'N',
                        'installment_plan': '000',
                        'installment_tenor': '00',
                        'generic_data': '',
                        'reff_number': paymentline.payment_edc_rrn,
                        'original_date': '',
                        'bca_filler': '',
                    }
                }

                self.paymentEdcBlockUi('Connecting to EDC Driver...');
                let result = await self.makeRequestEDC({
                    url: url,
                    data: data,
                });

                if(result.status == 'error'){
                    self.paymentEdcUnblockUi();
                    Gui.showPopup('ErrorPopup', {
                        title: 'Error',
                        body: result.message,
                    });
                    return;
                }

                if(result.status == 'waiting'){
                    self.paymentEdcBlockUi( `Checking Payment Status` );
                    self.paymentEdcBlockUiCountdown();
                    let payment = await self.checkPaymentEDC(order_number);
                    console.log('Check Payment Qris:: EDC Data: - ' , payment); 
                    if(payment.status == 'Expired'){
                        self.paymentEdcUnblockUi();
                        Gui.showPopup('ErrorPopup', {
                            title: payment.status,
                            body: payment.message,
                        });
                        return;
                    }

                    if(payment.resp_code != '00'){
                        self.paymentEdcUnblockUi();
                        let error_message = self.getErrorCodeMessage(payment.resp_code);
                        $('.payment-edc-qris .payment-edc-label').text(error_message);

                        if(!error_message){
                            error_message += '\n\n';
                        }
                        if(!payment.message){
                            error_message += payment.message;
                        }
                        Gui.showPopup('ConfirmPopup', {
                            title: 'Payment Status (' + payment.resp_code + ')',
                            body: error_message,
                        });
                        return;
                    }

                    paymentline.payment_edc_state = 'paid';
                    paymentline.payment_type = payment.trans_type;
                    paymentline.approval_code = payment.data.approval_code;
                    paymentline.is_payment_edc = true;

                    order.is_payment_edc = true;
                    order.payment_edc_id = payment.data.id;
                    self.paymentEdcBlockUi('Payment Success');
                    $('.payment-edc-qris .payment-edc-label').html(`Approval Code: <span>${self.getApprovalCode(paymentline)}</span>`);
                    $('.edc-payment-loader-wrap .edc-payment-countdown').hide();

                    self.render();
                    setTimeout(function(){
                        self.paymentEdcUnblockUi();
                    }, 1000);
                }
            }
        } 

        async makeRequestEDC(vals){
            let url = vals.url;
            let dataJSON = JSON.stringify(vals.data);
            let xhttp = new XMLHttpRequest();

            return new Promise(function (resolve, reject) {
                let xhr = new XMLHttpRequest();
                xhr.open('POST', url);
                xhr.onload = function () {
                    if (this.status >= 200 && this.status < 300) {
                        console.log('Result Request EDC:', xhr.response)
                        if(xhr.response){
                            if(JSON.parse(xhr.response).status == 'success'){
                                return resolve({
                                    'status': 'waiting',
                                    'message': 'waiting for EDC callback',
                                    'response': xhr.response
                                });
                            }
                        }

                        return resolve({
                            'status': 'error',
                            'message': 'Cannot connect to EDC Driver: \n' + xhr.response,
                            'response': xhr.response
                        });
                    }

                    return resolve({
                        'status': 'error',
                        'message': 'Cannot connect to EDC Driver: \n' + xhttp.statusText,
                        'response': {
                            status: this.status,
                            statusText: xhr.statusText
                        }
                    });
                };
                xhr.onerror = function () {
                    resolve({
                        'status': 'error',
                        'message': 'Cannot connect to EDC Driver! \n' + xhttp.statusText,
                        'response': {
                            status: this.status,
                            statusText: xhr.statusText
                        }
                    });
                };
                xhr.send(dataJSON);
            });
        }

        async checkPrintedStatus(order_number){
            const self = this
            timerCounterPrintedStatus = parseInt(countdownEDC / 5) + 1;
            return new Promise(function (resolve, reject) {
                clearInterval(timer);
                timer = setInterval(function () {
                    --timerCounterPrintedStatus;
                   
                    let vals = {
                        'domain': [['order_number','=',order_number], ['trans_type','=','31']],
                        'fields': ['id','payment_state','resp_code','invoice_number','order_number','approval_code','rrn'],
                        'limit': 1,
                        'order': 'create_date desc',
                    };
                    let args = [[], vals];
                    self.rpc({
                        model: 'pos.payment.edc',
                        method: 'get_payment', 
                        args: args
                    },{
                        shadow: true,
                        timeout: 2000 // 2 seconds
                    }).then(function (payments) {
                        console.log('Check EDC Qris: Checking (', order_number, ') - ' ,timerCounterPrintedStatus, ' - ' , payments)
                        if(payments.length > 0){
                            clearInterval(timer);
                            let payment = payments[0];
                            resolve({
                                'status': payment.payment_state,
                                'message': '',
                                'data': payment,
                                'resp_code': payment.resp_code,
                            });
                        }
                        if(timerCounterPrintedStatus <= 0){
                            clearInterval(timer);
                            resolve({
                                'status': 'Expired',
                                'message': 'Payment Expired'
                            });
                        }
                    
                    }, function (error) {
                        if(timerCounterPrintedStatus <= 0){
                            clearInterval(timer);
                            resolve({
                                'status': 'Expired',
                                'message': 'Payment Expired.'
                            });
                        }
                        return null;
                    });
                }, 5000);
            });
        }

        async checkPaymentEDC(order_number){
            const self = this
            timerCounterCheckPayment = parseInt(countdownEDC / 5) + 1;
            return new Promise(function (resolve, reject) {
                clearInterval(timer);
                timer = setInterval(function () {
                    --timerCounterCheckPayment;

                    let vals = {
                        'domain': [['order_number','=',order_number], ['trans_type','=','32']],
                        'fields': ['id','payment_state','resp_code','invoice_number','order_number','approval_code','rrn'],
                        'limit': 1,
                        'order': 'create_date desc',
                    };
                    let args = [[], vals];
                    self.rpc({
                        model: 'pos.payment.edc',
                        method: 'get_payment', 
                        args: args
                    },{
                        shadow: true,
                        timeout: 2000 // 2 seconds
                    }).then(function (payments) {
                        console.log('Check Payment Qris: Checking (', order_number, ') - ' ,timerCounterCheckPayment, ' - ' , payments)
                        if(payments.length > 0){
                            clearInterval(timer);
                            let payment = payments[0];
                            resolve({
                                'status': payment.payment_state,
                                'message': '',
                                'data': payment,
                                'resp_code': payment.resp_code,
                            });
                        }
                        if(timerCounterCheckPayment <= 0){
                            clearInterval(timer);
                            resolve({
                                'status': 'Expired',
                                'message': 'Payment Expired'
                            });
                        }
                    
                    }, function (error) {
                        if(timerCounterCheckPayment <= 0){
                            clearInterval(timer);
                            resolve({
                                'status': 'Expired',
                                'message': 'Payment Expired.'
                            });
                        }
                        return null;
                    });
                }, 5000);
            });
        }

        paymentEdcBlockUi(new_text){
            let text = _t('Waiting for EDC payment');
            if(new_text){
                let $text = $('.edc-payment-loader-wrap .edc-payment-text');
                if($text.length){
                    $text.text(_t(new_text));
                    return;
                }

                text = _t(new_text);
            }

            $('body').append(`
                <div class="edc-payment-loader-wrap">
                    <div style=" display: block; text-align: center;">
                        <span class="edc-payment-loader"></span>
                        <div id="edc-payment-countdown" class="edc-payment-countdown" style="display:none;">--:--</div>
                        <div class="edc-payment-text">${text}</div>
                    </div>
                    <div class="edc-payment-backdrop"></div>
                </div>`);
        }

        paymentEdcBlockUiCountdown(){
            let self = this;
            let $wrap = $('.edc-payment-loader-wrap');
            let $countdown = $wrap.find('.edc-payment-countdown');

            function doCountdown(){
                let count = countdownEDC;
                const secondsToMinSecPadded = time => {
                    const minutes = `${Math.floor(time / 60)}`.padStart(2, "0");
                    const seconds = `${time - minutes * 60}`.padStart(2, "0");
                    return `${minutes}:${seconds}`;
                };

                let countdownInterval = setInterval(function() {
                    let timeDisplay = secondsToMinSecPadded(count);
                    $countdown.text(timeDisplay);
                    $countdown.show();

                    count--;
                    if(count < 0){
                        $wrap.addClass('timeout');
                        $countdown.text('00:00');
                        clearInterval(countdownInterval);
                    }
                }, 1000);
                
                let $el = $(`<div class="edc-payment-cancel-request"><i class="fa fa-times"></i>Cancel Request</div>`);
                $wrap.find('.edc-payment-text').after($el);
                $el.click(function (e) {
                    self.paymentEdcUnblockUi();
                    clearInterval(countdownInterval);
                    clearInterval(timer);
                });
            }
            
            if($countdown.length){
                doCountdown();
            }
        }

        paymentEdcUnblockUi(){
            $('.edc-payment-loader-wrap').remove();
        }

        getErrorCodeMessage(resp_code){
            let error_status = {
                '54': 'Decline Expired Card',
                '55': 'Decline Incorrect PIN',
                'P2': 'Read Card Error',
                'P3': 'User press Cancel on EDC',
                'Z3': 'EMV Card Decline',
                'CE': 'Connection Error/Line Busy',
                'TO': 'Connection Timeout',
                'PT': 'EDC Problem',
                'aa': 'Decline (aa represent two digit alphanumeric value from EDC)',
                'S2': 'Tansaksi gagal Ulangi Transaksi di EDC',
                'S3': 'TXN Belum diproses minta Scan QR',
                'S4': 'TXN Expired Ulangi Transaksi',
                'TN': 'Topup Tunai Not Ready',
            }

            if(typeof error_status[resp_code] != 'undefined'){
                return error_status[resp_code];
            }
            return 'Response Code: ' + resp_code;
        }
    }

    PaymentLineEdcQris.template = 'PaymentLineEdcQris';
    Registries.Component.add(PaymentLineEdcQris);
    return PaymentLineEdcQris;
});