odoo.define('equip3_pos_printer_bluetooth.KitchenReceiptScreen', function (require) {
    "use strict";
    const {Printer} = require('point_of_sale.Printer');
    const {useRef} = owl.hooks;
    const ReceiptScreen = require('point_of_sale.AbstractReceiptScreen')
    const Registries = require('point_of_sale.Registries');

    const KitchenReceiptScreen = (ReceiptScreen) => {

        class KitchenReceiptScreen extends ReceiptScreen {
            constructor() {
                super(...arguments);
                this.orderReceipt = useRef('order-kot-receipt');
                this.changes = arguments[1].changes
                var order = this.env.pos.get_order()

            }

            mounted() {
                this.printReceipt();
            }

            New_Order() {
                this.env.pos.add_new_order();
                this.trigger('close-temp-screen');
            }

            confirm() {
                this.props.resolve({confirmed: true, payload: null});
                this.trigger('close-temp-screen');
            }

            whenClosing() {
                this.confirm();
            }

            get currentOrder() {
                return this.env.pos.get_order();
            }

            get computeChanges_orderlines() {
                var add = this.changes.new;
                var rem = this.changes.cancelled;
                return {
                    'all': add.concat(rem),

                };

            }

            async printReceipt() {
                var printers = this.env.pos.printers;
                const printer = new Printer(null, this.env.pos);
                var xhttp = new XMLHttpRequest();
                for (var i = 0; i < $(".pos-receipt").length; i++) {
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
                        'copies': 1,
                        'openCashDrawer': false,
                        'order': receipt,
                        'image_logo': receipt.company.logo,
                    };
                    var receiptJSON = JSON.stringify(receiptObj);
                    xhttp.send(receiptJSON);
                }
                // if(true) {
                //     let result = await this._printReceipt();
                // }
            }

            async tryReprint() {
                await this._printReceipt();
            }

        }

        KitchenReceiptScreen.template = 'KitchenReceiptScreen';
        return KitchenReceiptScreen
    }
    Registries.Component.addByExtending(KitchenReceiptScreen, ReceiptScreen)


})
