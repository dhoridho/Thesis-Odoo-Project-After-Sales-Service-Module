odoo.define('wysiwyg.widgets.VideoDialog', function (require) {
    'use strict';

    var core = require('web.core');
    var Dialog = require('wysiwyg.widgets.Dialog');

    var _t = core._t;
    var recordedBlobs = [];
    /**
     * Allows to customize video content and style.
     */
    var VideoDialog = Dialog.extend({
        template: 'wysiwyg.widget.video',
        xmlDependencies: (Dialog.prototype.xmlDependencies || []).concat([
            '/web_elearning_video/static/src/xml/wysiwyg.xml'
        ]),
        events: {
            'click .note-record-btn': '_onClickStart',
            'click .note-record-stop-btn': '_onClickStop',
            'click .note-video-play': '_onPlayVideo',
            'click .note-video-download': '_onDownloadVideo',
        },

        /**
         * @constructor
         */
        init: function (parent, media, editable) {
            this._super(parent, _.extend({}, {
                title: _t("Add Video")
            }, {}));
            this.constraints = { audio: true, video: true };
            this.mediaRecorder;
            this.media = media;
            this.editable = editable;
        },
        start: function () {
            recordedBlobs = []
            this.gumVideo = this.$('video.gum').get(0);
            this.startButton = this.$('button.note-record-btn');
            this.stopButton = this.$('button.note-record-stop-btn');
            this.playButton = this.$('button.note-video-play');
            this.downloadButton = this.$('button.note-video-download');
            this.recordedVideo = this.$('video.note-video-input');
            var self = this;
            navigator.mediaDevices.getUserMedia(this.constraints)
                .then(stream => {
                    self.gumVideo.srcObject = stream;
                    window.stream = stream;
                })
                .catch(error => {
                    alert('Error accessing media devices.', error);
                });
        },
        _onClickStart: function (ev) {
            recordedBlobs = []
            var options = { mimeType: 'video/webm;codecs=vp9', bitsPerSecond: 100000 };
            try {
                this.mediaRecorder = new MediaRecorder(window.stream, options);
            } catch (e0) {
                console.log('Unable to create MediaRecorder with options Object: ', options, e0);
                try {
                    options = { mimeType: 'video/webm;codecs=vp8', bitsPerSecond: 100000 };
                    this.mediaRecorder = new MediaRecorder(window.stream, options);
                } catch (e1) {
                    console.log('Unable to create MediaRecorder with options Object: ', options, e1);
                    try {
                        options = 'video/mp4';
                        this.mediaRecorder = new MediaRecorder(window.stream, options);
                    } catch (e2) {
                        alert('MediaRecorder is not supported by this browser.');
                        console.error('Exception while creating MediaRecorder:', e2);
                        return;
                    }
                }
            }
            var self = this;
            ev.currentTarget.disabled = true;
            this.stopButton.get(0).disabled = false;
            this.playButton.get(0).disabled = true;
            this.downloadButton.get(0).disabled = true
            this.mediaRecorder.ondataavailable = self.handleDataAvailable;
            this.mediaRecorder.start(10);
        },
        _onClickStop: function (ev) {
            this.mediaRecorder.stop();
            ev.currentTarget.disabled = true;
            this.playButton.get(0).disabled = false;
            this.startButton.get(0).disabled = false;
            this.downloadButton.get(0).disabled = false
        },
        handleDataAvailable: function (event) {
            if (event.data && event.data.size > 0) {
                recordedBlobs.push(event.data);
            }
        },
        _onPlayVideo: function (ev) {
            var type = (recordedBlobs[0] || {}).type;
            var superBuffer = new Blob(recordedBlobs, { type });
            this.recordedVideo.get(0).src = window.URL.createObjectURL(superBuffer);
        },
        _onDownloadVideo: function (ev) {
            var blob = new Blob(recordedBlobs, { type: 'video/webm' });
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'recording.webm';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () {
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }, 100);
        },
        save: async function () {
            if (recordedBlobs.length !== 0) {
                const attachmentObj = await this.addAttachment();
                this.recordedVideo.get(0).removeAttribute('src');
                this.recordedVideo.get(0).load();
                if (typeof (window.stream) == "object") {
                    window.stream.getTracks().forEach((track) => {
                        track.stop();
                    });
                }
                this.final_data = attachmentObj;
                let url = window.location.origin + '/web/content/' + attachmentObj.id + '?controls=1';
                let videoUrl = `
                    <div class="media_iframe_video iframe_custom o_we_selected_image">
                        <div class="media_iframe_video_size" contenteditable="false" style="padding-bottom:10px;">&nbsp;</div>
                        <video controls="controls">
                            <source src="${url}" type="video/webm" />
                        </video>
                    </div><br/>`;
                var pTag = this.editable.find('p');
                if (pTag.length > 1) {
                    pTag.last().append(videoUrl);
                } else {
                    pTag.append(videoUrl);
                }
            }
            this.close();
        },

        destroy: function () {
            if (typeof (window.stream) == "object") {
                window.stream.getTracks().forEach((track) => {
                    track.stop();
                });
            }
            return this._super(...arguments);
        },

        blobToBase64: blob => {
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            return new Promise(resolve => {
                reader.onloadend = () => {
                    resolve(reader.result);
                };
            });
        },
        addAttachment: async function () {
            let videoAttachment;
            if (recordedBlobs) {
                let type = (recordedBlobs[0] || {}).type;
                let superBuffer = new Blob(recordedBlobs, { type });
                const bs64Video = await this.blobToBase64(superBuffer)
                videoAttachment = await this._rpc({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        'name': 'recording.webm',
                        'data': bs64Video.split(',')[2],
                        'res_id': $.summernote.options.res_id,
                        'res_model': $.summernote.options.res_model,
                    },
                })
            }
            return videoAttachment;
        }
    });
    return VideoDialog;
});
