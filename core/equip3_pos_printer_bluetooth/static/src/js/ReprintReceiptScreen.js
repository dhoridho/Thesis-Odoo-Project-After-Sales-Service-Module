odoo.define('equip3_pos_printer_bluetooth.ReprintReceiptScreen', function (require) {
    'use strict';
    const {Printer} = require('point_of_sale.Printer');
    const ReprintReceiptScreen = require('point_of_sale.ReprintReceiptScreen');
    const Registries = require('point_of_sale.Registries');

    const customReprintReceiptScreen = (ReprintReceiptScreen) => {
        class customReprintReceiptScreen extends ReprintReceiptScreen {

            get compute_product() {
                var add = [];
                var product = this.props.order.get_orderlines();
                if (product.length > 0) {
                    if (this.env.pos.config.receipt_types_views === "labelReceipt") {
                        for (var n = 0; n < product.length; n++) {
                            for (var nq = 0; nq < product[n].quantity; nq++) {
                                add.push(product[n])
                            }
                        }
                    }
                }
                return {
                    'products': add,

                };
            }

            async printReceiptAndLabel() {
                console.log('Reprint: Print Receipt and Category')
                if (this.env.pos.config.pos_bluetooth_printer) {
                    let receipt = this.env.pos.get_order().get_receipt_bluetooth_printer();
                    const printer = new Printer(null, this.env.pos);
                    var xhttp = new XMLHttpRequest();
                    const receiptString = this.orderReceipt.comp.el.outerHTML;
                    const ticketImage = await printer.htmlToImg(receiptString);
                    xhttp.open("POST", "http://localhost:9100", true);
                    var receiptObj = {
                        // image: ticketImage, text: ""
                        'type': 'print_receipt_and_category',
                        'copies': 1,
                        'openCashDrawer': false,
                        'order': receipt,
                        'image_logo': receipt.company.logo,
                    };
                    var receiptJSON = JSON.stringify(receiptObj);
                    xhttp.send(receiptJSON);
                    await this.printLabel()
                }
            }

            async printReceipt() {
                console.log('Reprint: Print Receipt')
                if (this.env.pos.config.pos_bluetooth_printer) {
                    let receipt = this.env.pos.get_order().get_receipt_bluetooth_printer();
                    const printer = new Printer(null, this.env.pos);
                    var xhttp = new XMLHttpRequest();
                    const receiptString = this.orderReceipt.comp.el.outerHTML;
                    const ticketImage = await printer.htmlToImg(receiptString);
                    xhttp.open("POST", "http://localhost:9100", true);
                    var receiptObj = {
                        // image: ticketImage, text: ""
                        'type': 'print_receipt',
                        'copies': 1,
                        'openCashDrawer': false,
                        'order': receipt,
                        'image_logo': receipt.company.logo,
                    };
                    var receiptJSON = JSON.stringify(receiptObj);
                    xhttp.send(receiptJSON);
                } else if (this.env.pos.proxy.printer && this.env.pos.config.iface_print_skip_screen) {
                    let result = await this._printReceipt();
                    if (result)
                        this.showScreen('TicketScreen', {reuseSavedUIState: true});
                }
            }

            async printLabel() {
                console.log('Reprint: Print Category')
                if (this.env.pos.config.pos_bluetooth_printer) {
                    var printers = this.env.pos.printers;
                    const printer = new Printer(null, this.env.pos);
                    var xhttp = new XMLHttpRequest();
                    for (var i = 1; i < $(".pos-receipt").length; i++) {
                        let receipt = this.env.pos.get_order().get_receipt_bluetooth_printer();
                        const receiptString = $(".pos-receipt")[i].outerHTML;
                        const ticketImage = await printer.htmlToImg(receiptString);
                        var categories_id = $(".pos-receipt")[i].getElementsByTagName("b")[0].innerHTML
                        for (var c = 0; c < printers.length; c++) {
                            var port = 0;
                            for (var d = 0; d < printers[c].config.product_categories_ids.length; d++) {
                                if (printers[c].config.product_categories_ids[d] == categories_id) {
                                    port = printers[c].config.EasyERPS_app_port;
                                    var url = "http://localhost:" + port
                                    break;
                                }
                            }
                            if (port != 0) {
                                break;
                            }
                        }
                        xhttp.open("POST", url, true);
                        var receiptObj = {
                            // image: ticketImage, text: ""
                            'type': 'print_category',
                            'copies': 1,
                            'openCashDrawer': false,
                            'order': receipt,
                            'image_logo': receipt.company.logo,
                        };
                        var receiptJSON = JSON.stringify(receiptObj);
                        xhttp.send(receiptJSON);
                    }
                }
            }
        }

        return customReprintReceiptScreen;
    };
    Registries.Component.extend(ReprintReceiptScreen, customReprintReceiptScreen);

});
