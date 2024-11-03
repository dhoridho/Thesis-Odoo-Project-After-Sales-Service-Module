odoo.define('equip3_pos_general_contd.ImportFilePopup', function (require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const {useState} = owl.hooks;
    
    class ImportFilePopup extends AbstractAwaitablePopup {
        constructor(){
            super(...arguments);
            this.data = [];
            this.state = useState({ 'import_state': '' });
        }

        async import(){
            let self = this;
            let $i = $('#import_file_local_order_log'); 
            if(!$i.length){
                return;
            }
            let ifile = $i[0];
            $i.removeClass('has-error');
            if(ifile.files.length == 0){
                $i.addClass('has-error');
                return;
            }
            self.state.import_state = 'loading';
            if (ifile.files && ifile.files[0]) {
                let file = ifile.files[0];
                let reader = new FileReader();
                reader.addEventListener('load', function (e) {
                    self.data = e.target.result;
                    self.state.import_state = 'done';
                    self.confirm();
                });
                reader.readAsBinaryString(file);
            }
        }

        async getPayload() {
            return {
                data: this.data,
            }
        }
    }


    ImportFilePopup.template = 'ImportFilePopup';
    ImportFilePopup.defaultProps = { title: 'Import' };
    Registries.Component.add(ImportFilePopup);
    return ImportFilePopup;

});