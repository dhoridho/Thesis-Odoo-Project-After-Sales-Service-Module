odoo.define('equip3_base_import_extend.binary_field_extend', function(require) {

    var BasicFields = require('web.basic_fields');

    BasicFields.FieldBinaryFile.include({
        _renderReadonly: function() {
            var self = this;
            var allowed_models = ['import.log', 'import.log.history'];
            self._super.apply(this, arguments); 
            if (self.value && allowed_models.includes(self.model)) {
                self.$el.empty().append($("<span/>").addClass('fa fa-download mr-2'));
                if (self.recordData.id) {
                    self.$el.css('cursor', 'pointer');
                } else {
                    self.$el.css('cursor', 'not-allowed');
                }
                if (self.filename_value) {
                    self.$el.append(" " + self.filename_value);
                }
            }
        },
    });
});
