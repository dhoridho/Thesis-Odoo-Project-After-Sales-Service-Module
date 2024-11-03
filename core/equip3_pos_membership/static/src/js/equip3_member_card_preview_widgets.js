odoo.define('equip3_pos_membership.equip3_member_card_preview', function (require) {
    "use strict";

  var basic_fields = require('web.basic_fields');
  var FieldChar = basic_fields.FieldChar;
  var registry = require('web.field_registry');
  var session = require('web.session');

  var Equip3MemberCardPreview = FieldChar.extend({
      _renderReadonly: function () {
          let self = this;
          var res = this._super.apply(this, arguments);
          let value = { 'barcode_card': '', 'qrcode_card': '' }
          if(self.value){
            value = JSON.parse(self.value);
          }
          if(!self.value){
            return res;
          }

          let $prevew = $(`
            <div class="member_card_preview">
              <div class="o_field_radio o_vertical o_field_widget">
                  <div class="custom-control custom-radio o_radio_item" style="padding-left: 0;">
                      <input type="radio" data-type="barcode" class="custom-control-input o_radio_input" checked="true" name="c_radio8000000" id="c_radio8000000_barcode">
                      <label class="custom-control-label o_form_label" for="c_radio8000000_barcode">Barcode</label>
                  </div>
                  <div class="custom-control custom-radio o_radio_item">
                      <input type="radio" data-type="qrcode" class="custom-control-input o_radio_input" name="c_radio8000000" id="c_radio8000000_qrcode">
                      <label class="custom-control-label o_form_label" for="c_radio8000000_qrcode">QR</label>
                  </div>
              </div>
              <div class="preview_card_img" data-type="barcode"> 
                   Member Card
              </div>
            </div>
          `);
          $prevew.find('.preview_card_img').html(value.barcode_card);

          $prevew.find('input[type="radio"]').change(function(e) {
            let $this = $(this);
            let $target = $('.member_card_preview .preview_card_img');
            $target.attr('src', $this.attr('data-img-url'));
            if($this.attr('data-type') == 'barcode'){
              $target.attr('data-type', 'barcode');
              $target.html(value.barcode_card);
            }else{
              $target.attr('data-type', 'qrcode');
              $target.html(value.qrcode_card);
            }
          });

          self.$el.addClass('oe_hidden');
          setTimeout(() => { 
            self.$el.after($prevew); 
            self.$el.addClass('oe_hidden');
          }, 100);
          return res;
      },
  });

  registry.add("equip3_member_card_preview", Equip3MemberCardPreview);
});
