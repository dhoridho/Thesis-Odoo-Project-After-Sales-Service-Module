odoo.define('equip3_pos_printer_bluetooth.ReportScreen', function (require) {
    'use strict';

    const {Printer} = require('point_of_sale.Printer');
    const {is_email} = require('web.utils');
    const {useRef, useContext} = owl.hooks;
    const {useErrorHandlers, onChangeOrder} = require('point_of_sale.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');
    const session = require('web.session');
    const {useState} = owl.hooks;

    const ReportScreen = (AbstractReceiptScreen) => {
        class ReportScreen extends AbstractReceiptScreen {
            constructor() {
                super(...arguments);
                this.report_html = arguments[1].report_html
                useErrorHandlers();
                this.orderReceipt = useRef('order-receipt');
                const order = this.currentOrder;
                if (order) {
                    const client = order.get_client();
                    this.orderUiState = useContext(order.uiState.ReceiptScreen);
                    this.orderUiState.inputEmail = this.orderUiState.inputEmail || (client && client.email) || '';
                    this.is_email = is_email;
                }
            }

            mounted() {
                $(this.el).find('.pos-receipt-container').append(this.report_html)
                setTimeout(async () => await this.handleAutoPrint(), 0);
            }

            async sendReceiptViaWhatsApp() {
                let {confirmed, payload: number} = await this.showPopup('NumberPopup', {
                    title: this.env._t("What a WhatsApp Number need to send ?"),
                    startingValue: 0
                })
                if (confirmed) {
                    let mobile_no = number
                    let {confirmed, payload: messageNeedSend} = await this.showPopup('TextAreaPopup', {
                        title: this.env._t('What message need to send ?'),
                        startingValue: ''
                    })
                    if (confirmed) {
                        let message = messageNeedSend
                        const printer = new Printer(null, this.env.pos);
                        const ticketImage = await printer.htmlToImg(this.props.report_html);
                        let responseOfWhatsApp = await this.rpc({
                            model: 'pos.config',
                            method: 'send_receipt_via_whatsapp',
                            args: [[], this.env.pos.config.id, ticketImage, mobile_no, message],
                        }, {
                            shadow: true,
                            timeout: 60000
                        });
                        if (responseOfWhatsApp && responseOfWhatsApp['id']) {
                            return this.showPopup('ConfirmPopup', {
                                title: this.env._t('Successfully'),
                                body: this.env._t("Receipt send successfully to your Client's Phone WhatsApp: ") + mobile_no,
                                disableCancelButton: true,
                            })
                        } else {
                            return this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: this.env._t("Send Receipt is fail, please check WhatsApp API and Token of your pos config or Your Server turn off Internet"),
                                disableCancelButton: true,
                            })
                        }
                    }
                }
            }

            async onSendEmail() {
                if (!this.orderUiState) {
                    return false
                }
                if (!is_email(this.orderUiState.inputEmail)) {
                    this.orderUiState.emailSuccessful = false;
                    this.orderUiState.emailNotice = 'Invalid email.';
                    return;
                }
                try {
                    await this._sendReceiptToCustomer();
                    this.orderUiState.emailSuccessful = true;
                    this.orderUiState.emailNotice = 'Email successfully sent !'
                } catch (error) {
                    this.orderUiState.emailSuccessful = false;
                    this.orderUiState.emailNotice = 'Sending email failed. Please try again.'
                }
            }

            get currentOrder() {
                return this.env.pos.get_order();
            }

            back() {
                if (this.props.closeScreen) {
                    window.location = '/web#action=equip3_pos_masterdata.point_of_sale_portal'
                    return true
                }
                this.trigger('close-temp-screen');
                if (this.env.pos.config.sync_multi_session && this.env.pos.config.screen_type == 'kitchen') {
                    return this.showScreen('KitchenScreen', {
                        'selectedOrder': this.props.orderRequest
                    })
                } else {
                    return this.showScreen('ProductScreen')
                }

            }

            async newOrder(){
                this.currentOrder.finalize(); 
                if (!this.currentOrder) {
                    this.env.pos.add_new_order();
                }
                this.showScreen('ProductScreen', {});
            }

            async printReceipt() {
                const printer = new Printer(null, this.env.pos);
                let printers = this.env.pos.printers;
                let receipt = {}
                let receiptObj = {}
                let last_order = null;
                let orderReceipt = null;
                let from = 'order';

                console.log('Start: Print Receipt, printers(',printers.length,')');

                let reprint_receipt = false;
                if($('div.pos-receipt span:contains("REPRINT RECEIPT")').length){
                    reprint_receipt = true
                }
                if($('div.pos-receipt p:contains("REPRINT RECEIPT")').length){
                    reprint_receipt = true
                }

                if(reprint_receipt){
                    from = 'order_history';
                }else if($('img.pos-receipt-logo').length > 0){
                    from = 'checker';
                }else if(this.props.TakeAway){
                    from = 'takeaway';
                }

                console.log('Start: Print Receipt, from(',from,')');

                if (from=='checker'){
                    last_order = this.env.pos.get_order();
                }else if (from=='order_history'){
                    last_order = this.props.order;
                }else if (from=='order' || from=='takeaway'){
                    orderReceipt = this.props.orderReceipt;
                }
                if(last_order){
                    receipt = last_order.get_receipt_bluetooth_printer();
                }

                var port = false;
                var url = '9100';
                if(printers.length > 1){
                    for (var c = 0; c < printers.length; c++) {
                        if(printers[c].config.EasyERPS_app_port == 9100) {
                            port = printers[c].config.EasyERPS_app_port || '9100';
                            url = "http://localhost:" + port
                            break
                        }
                    }
                    if (!port){
                        port = printers[0].config.EasyERPS_app_port || '9100';
                        url = "http://localhost:" + port
                    }
                }
                else if(printers.length== 1){
                    port = printers[0].config.EasyERPS_app_port || '9100';
                    url = "http://localhost:" + port
                }
                else{
                    if (this.env.pos.proxy.printer || (this.props.report_xml && this.env.pos.config.local_network_printer && this.pos.config.local_network_printer_ip_address && this.env.pos.config.local_network_printer_port)) {
                        this.handleAutoPrint()
                    } else {
                        this._printWeb()
                    }
                }

                if(printers.length >= 1){
                    let table = '';
                    let guest = '';
                    let floor = '';
                    if (from == 'checker'){
                        if(last_order){
                            if (last_order.table){
                                table = last_order.table.name;
                                guest = last_order.table.guest;
                            }
                        }
                        receiptObj = {
                            'from':from,
                            'logo_image': '',
                            'company_name': '',
                            'company_website': '',
                            'user':receipt.cashier,
                            'table':table,
                            'quest':guest,
                            'order_line':receipt.orderlines_simple,
                            'total_item':receipt.total_item,
                            'order_number':receipt.name
                        }
                        if(receipt.company){
                            receiptObj['logo_image'] = receipt.company.logo;
                            receiptObj['company_name'] = receipt.company.name;
                            receiptObj['company_website'] = receipt.company.website;
                        }
                    }
                    if(from == 'order_history') {
                        receiptObj = {
                            'from':from,
                            'order_number':receipt.name,
                            'company_name': '',
                            'company_phone': '',
                            'user':receipt.cashier,
                            'order_line':receipt.orderlines_simple,
                            'subtotal':receipt.subtotal,
                            'tax':receipt.total_tax,
                            'total':receipt.total_with_tax,
                            'discount':receipt.total_discount,
                            'cash':receipt.paymentlines,
                            'change':receipt.change
                        }
                        if(receipt.company){
                            receiptObj['company_name'] = receipt.company.name;
                            receiptObj['company_phone'] = receipt.company.phone;
                        }
                    }
                    if(from == 'order' || from == 'takeaway') {
                        let order_line = [];
                        if(orderReceipt.new){
                            for (var i = orderReceipt.new.length - 1; i >= 0; i--) {
                                let line = orderReceipt.new[i];
                                order_line.push({
                                    'item': line.name,
                                    'item_qty': line.qty,
                                    'unit_name': line.uom.display_name,
                                    'amount': false,
                                });
                            }
                        }
                        receiptObj = {
                            'from': from,
                            'order_number': orderReceipt.name,
                            'order_ticket': orderReceipt.ticket_number,
                            'floor': orderReceipt.table,
                            'table': orderReceipt.floor,
                            'order_status': orderReceipt.state,
                            'order_time': orderReceipt.time.hours + ':'+ orderReceipt.time.minutes,
                            'order_line': order_line,
                        };
                    }

                    let printers_values = []
                    let printers_categories = this.env.pos.printers;
                    for (let i = 0; i < printers_categories.length; i++) {
                        let printer = printers_categories[i].config;
                        let printer_values = {
                            'id': printer.id,
                            'name': printer.name,
                            'port': printer.EasyERPS_app_port || '',
                        }
                        if(printer.product_categories_ids){
                            printer_values['product_categories_ids'] = printer.product_categories_ids;

                            let product_categories = [];
                            for (let cIdx in this.env.pos.pos_category_by_id ) {
                                let cat = this.env.pos.pos_category_by_id[cIdx];
                                if(printer.product_categories_ids.includes(cat.id)){
                                    product_categories.push({
                                        'id': cat.id,
                                        'name': cat.name,
                                        'category_type': cat.category_type,
                                        'child_id': cat.child_id,
                                    })
                                }
                            }
                            printer_values['product_categories'] = product_categories;
                            printers_values.push(printer_values);
                        }

                    }
                    receiptObj['printers'] = printers_values;

                    if(from == 'order_history'){
                        receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_reprint_receipt(this.props.order);
                    }

                    if(from == 'checker'){
                        receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_category();
                    }

                    if(from == 'order' || from == 'takeaway'){
                        receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_queue(receiptObj);
                    }

                    console.log('Data: Print Receipt ~ ',receiptObj);
                    var receiptJSON = JSON.stringify(receiptObj);
                    var xhttp = new XMLHttpRequest();
                    xhttp.onreadystatechange = function() {
                        if (xhttp.readyState == XMLHttpRequest.DONE) {
                            console.log('Finish: Print Receipt ~ ', xhttp.responseText);
                        }
                    }
                    xhttp.open("POST", url, true);
                    xhttp.send(receiptJSON);
                }
                
            }

            async handleAutoPrint() {
                if (this.props.report_xml && this.env.pos.proxy.printer && this.env.pos.config.proxy_ip) {
                    this.env.pos.proxy.printer.printXmlReceipt(this.props.report_xml);
                }
                if (this.props.report_html && this.env.pos.proxy.printer && !this.env.pos.config.proxy_ip) {
                    this.env.pos.proxy.printer.print_receipt(this.props.report_html);
                }
                if (this.props.report_xml && this.env.pos.config.local_network_printer && this.env.pos.config.local_network_printer_ip_address && this.env.pos.config.local_network_printer_port) {
                    const printer = new Printer(null, this.env.pos);
                    printer.printViaNetwork(this.props.report_xml, 1);
                }
            }


            async _sendReceiptToCustomer() {
                const printer = new Printer();
                const receiptString = this.orderReceipt.comp.el.outerHTML;
                const ticketImage = await printer.htmlToImg(receiptString);
                const order = this.currentOrder;
                const client = order.get_client();
                const orderName = order.get_name();
                const orderClient = {
                    email: this.orderUiState.inputEmail,
                    name: client ? client.name : this.orderUiState.inputEmail
                };
                const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
                await this.rpc({
                    model: 'pos.order',
                    method: 'action_receipt_to_customer',
                    args: [[order_server_id], orderName, orderClient, ticketImage],
                });
            }
        }

        ReportScreen.template = 'ReportScreen';
        return ReportScreen;
    };

    Registries.Component.addByExtending(ReportScreen, AbstractReceiptScreen);

    return ReportScreen;
});
