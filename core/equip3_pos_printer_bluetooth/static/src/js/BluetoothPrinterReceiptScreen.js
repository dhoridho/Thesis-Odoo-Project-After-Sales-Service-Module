odoo.define('equip3_pos_printer_bluetooth.ReceiptScreen', function (require) {
    "use strict";

    const {Printer} = require('point_of_sale.Printer');
    const Registries = require('point_of_sale.Registries');
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');

    const customReceiptScreen = ReceiptScreen => {
        class customReceiptScreen extends ReceiptScreen {

            constructor() {
                super(...arguments);
                var order = this.env.pos.get_order();
            }

            get currentOrder() {
                return this.env.pos.get_order();
            }

            get_is_openCashDrawer() {
                return this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change();
            }

            async handleAutoPrint() {
                if (this._shouldAutoPrint()) {
                    if (this.env.pos.config.bluetooth_print_auto) {
                        await this.printReceiptAndLabel();
                        if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                            this.whenClosing();
                        }
                    } else {
                        await this.printReceipt();
                        if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                            this.whenClosing();
                        }
                    }

                }
            }

            async printReceiptAndLabel() {
                console.log('Start: Print Receipt!!!')
                if (this.env.pos.config.pos_bluetooth_printer) {
                    let order = this.env.pos.get_order();
                    let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order);
                    console.log('Data: Print Receipt!!! ~ ',receiptObj);
                    let receiptJSON = JSON.stringify(receiptObj);
                    let xhttp = new XMLHttpRequest();
                    xhttp.onreadystatechange = function() {
                        if (xhttp.readyState == XMLHttpRequest.DONE) {
                            console.log('Finish: Print Receipt!!! ~ ', xhttp.responseText);
                        }
                    }
                    xhttp.onerror = function () {
                        console.error('Finish: Print Receipt!!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                    };
                    xhttp.open('POST', 'http://localhost:9100', true);
                    xhttp.send(receiptJSON);
                } else {
                    const isPrinted = await this._printReceipt();
                    if (isPrinted) {
                        this.currentOrder._printed = true;
                    }
                }

            }

            async printReceipt() {
                console.log('Start: Print Receipt!!')
                if (this.env.pos.config.pos_bluetooth_printer) {
                    let order = this.env.pos.get_order();
                    let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order);
                    console.log('Data: Print Receipt!! ~ ',receiptObj);
                    let receiptJSON = JSON.stringify(receiptObj);
                    let xhttp = new XMLHttpRequest();
                    xhttp.onreadystatechange = function() {
                        if (xhttp.readyState == XMLHttpRequest.DONE) {
                            console.log('Finish: Print Receipt!! ~ ', xhttp.responseText);
                        }
                    }
                    xhttp.onerror = function () {
                        console.error('Finish: Print Receipt!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                    };
                    xhttp.open('POST', 'http://localhost:9100', true);
                    xhttp.send(receiptJSON);

                } else {
                    const isPrinted = await this._printReceipt();
                    if (isPrinted) {
                        this.currentOrder._printed = true;
                    }
                }
            }


            async printLabel() {
                console.log('Start: Print Category!!!!')
                let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_category();
                console.log('Data: Print Category!!!! ~ ',receiptObj);
                let receiptJSON = JSON.stringify(receiptObj);
                let xhttp = new XMLHttpRequest();
                xhttp.onreadystatechange = function() {
                    if (xhttp.readyState == XMLHttpRequest.DONE) {
                        console.log('Finish: Print Category!!!! ~ ', xhttp.responseText);
                    }
                }
                xhttp.onerror = function () {
                    console.error('Finish: Print Category!!!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                };
                xhttp.open('POST', 'http://localhost:9100', true);
                xhttp.send(receiptJSON);
            }


        }

        return customReceiptScreen;
    };


    Registries.Component.extend(ReceiptScreen, customReceiptScreen);

});

