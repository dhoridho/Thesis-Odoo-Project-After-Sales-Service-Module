odoo.define('widget_image_recognition', function(require) {
    var core = require('web.core');
    var qweb = core.qweb;
    var Registry = require('web.field_registry');
    var BasicFields = require('web.basic_fields');

    var session = require('web.session');
    var utils = require('web.utils');
    var field_utils = require('web.field_utils');

    var ImageRecognition = BasicFields.FieldBinaryImage.extend({
        events: _.extend({}, BasicFields.FieldBinaryImage.prototype.events, {
            'click button.o-kanban-button-hide-face-recognition': '_hide_canvas_face_recognition',
        }),

        _hide_canvas_face_recognition: function () {
            $('.only-descriptor').toggle( "slow", function() {});
            $('.o-kanban-button-hide-face-recognition').toggleClass('badge-success');
            $('.o-kanban-button-hide-face-recognition').toggleClass('badge-warning');
        },
        start: function () {
            this._super.apply(this, arguments);
            console.log($('.token-count-title'));
        },
        _render: function () {
            this._super.apply(this, arguments);
            var self = this;
            var url = this.placeholder;
            if (this.value) {
                if (!utils.is_bin_size(this.value)) {
                    // Use magic-word technique for detecting image type
                    url = 'data:image/' + (this.file_type_magic_word[this.value[0]] || 'png') + ';base64,' + this.value;
                } else {
                    var field = this.nodeOptions.preview_image || this.name;
                    var unique = this.recordData.__last_update;
                    url = this._getImageUrl(this.model, this.res_id, field, unique);
                }
            }

            // if check in/out on mobile device photo 1:1 else 2:3
            var face_width = '600px';
            var face_height = '400px';
            if (this.recordData.ismobile_check_in &&
                (this.attrs.name =='webcam_check_in' || this.attrs.name == 'face_recognition_image_check_in'))
                var face_width = '400px';
            if (this.recordData.ismobile_check_out && 
                (this.attrs.name =='webcam_check_out' || this.attrs.name == 'face_recognition_image_check_out'))
                var face_width = '400px';
            var $img = $(qweb.render("ImageRecognition-img", {
                widget: this,
                url: url,
                face_width:face_width,
                face_height:face_height}));

            // override css size attributes (could have been defined in css files)
            // if specified on the widget
            var width = this.nodeOptions.size ? this.nodeOptions.size[0] : this.attrs.width;
            var height = this.nodeOptions.size ? this.nodeOptions.size[1] : this.attrs.height;

            if (width) {
                $img.attr('width', width);
                $img.css('max-width', width + 'px');
            }
            if (height) {
                $img.attr('height', height);
                $img.css('max-height', height + 'px');
            }
            this.$('> img').remove();
            this.$el.prepend($img);

            $img.one('error', function () {
                $img.attr('src', self.placeholder);
                self.do_warn(_t("Image"), _t("Could not display the selected image."));
            });

            //return this._super.apply(this, arguments);
        },
    });
    Registry.add('image_recognition', ImageRecognition);


});