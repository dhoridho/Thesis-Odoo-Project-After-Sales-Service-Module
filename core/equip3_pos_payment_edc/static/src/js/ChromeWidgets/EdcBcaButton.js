odoo.define('equip3_pos_payment_edc.EdcBcaButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');

    class EdcBcaButton extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        async onClick() {
            let {confirmed, payload: payload } = await Gui.showPopup('EdcBcaPopup', {'title': 'EDC BCA Test',} );
            if(confirmed){

                let dataJSON = JSON.stringify({
                    order_id: 54123, 
                    amount: 100000, 
                    customer: {
                        name: 'John', 
                        phone: '08512123123'
                    }
                });
                let xhttp = new XMLHttpRequest();
                xhttp.timeout = (5 * 60) * 1000; // 5 minutes
                xhttp.addEventListener("load", responseStatus);
                xhttp.addEventListener("error", responseStatus);
                xhttp.open('POST', payload.url, true);
                xhttp.send(dataJSON);
                function responseStatus(e){
                    if(e.type == 'error'){
                        alert('Network error');
                    }
                    if(e.type == 'load'){
                        if (xhttp.status < 400){
                            console.log('Request success: \n', xhttp.responseText)
                            Gui.showPopup('ErrorPopup', {
                                title: 'Success',
                                body: 'Response Status: ' + xhttp.responseText
                            })
                        }else{
                            console.log('Request failed:  \n', xhttp.statusText)
                            Gui.showPopup('ErrorPopup', {
                                title: 'Error',
                                body: xhttp.statusText
                            })
                        }
                    }
                }

            }
        }
    }

    EdcBcaButton.template = 'EdcBcaButton';
    ProductScreen.addControlButton({
        component: EdcBcaButton,
        condition: function() {
            return true;
        },
    });
    Registries.Component.add(EdcBcaButton);
    return EdcBcaButton;
});