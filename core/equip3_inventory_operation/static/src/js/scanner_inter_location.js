$(document).ready(function () {
    let selectedDeviceId;

    function decodeOnce(codeReader, selectedDeviceId, inputField, resultElement, videoElement, resetButton) {
        let video;
    
        if (resultElement === 'js_id_sh_stock_barcode_mobile_result_source_location') {
            video = "video_source_location";
        } else if (resultElement === 'js_id_sh_stock_barcode_mobile_result_dest_location') {
            video = "video_destination_location";
        } else {
            video = "video";
        }
        codeReader
            .decodeFromInputVideoDevice(selectedDeviceId, video)
            .then((result) => {
                // console.log(result);
                $(inputField).val(result.text);
                $(inputField).change();

                //RESET READER
                codeReader.reset();

                //HIDE VIDEO
                $(videoElement).hide();

                //HIDE STOP BUTTON
                $(resetButton).hide();

                //RESULT
                document.getElementById(resultElement).textContent = result.text;
            })
            .catch((err) => {
                console.error(err);
            });
    }

    function decodeContinuously(codeReader, selectedDeviceId, inputField, resultElement) {
        let video;
    
        if (resultElement === 'js_id_sh_stock_barcode_mobile_result_source_location') {
            video = "video_source_location";
        } else if (resultElement === 'js_id_sh_stock_barcode_mobile_result_dest_location') {
            video = "video_destination_location";
        } else {
            video = "video";
        }
        codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, video, (result, err) => {
            if (result) {
                // properly decoded qr code
                // console.log("Found QR code!", result);
                $(inputField).val(result.text);
                $(inputField).change();

                //RESULT
                document.getElementById(resultElement).textContent = result.text;
            }

            if (err) {
                if (err instanceof ZXing.NotFoundException) {
                    // console.log("No QR code found.");
                    //EMPTY INPUT
                    $(inputField).val("");
                    $(inputField).change();
                }
            }
        });
    }

    //HIDE STOP BUTTONS
    $("#js_id_sh_stock_barcode_mobile_reset_btn").hide();
    $("#js_id_sh_stock_barcode_mobile_reset_btn_source_location").hide();
    $("#js_id_sh_stock_barcode_mobile_reset_btn_dest_location").hide();

    const codeReaderMain = new ZXing.BrowserMultiFormatReader();
    const codeReaderSource = new ZXing.BrowserMultiFormatReader();
    const codeReaderDestination = new ZXing.BrowserMultiFormatReader();

    function initializeCameraSelection(codeReader, selectElementId) {
        codeReader.getVideoInputDevices().then(function (result) {
            const sourceSelect = document.getElementById(selectElementId);

            _.each(result, function (item) {
                const sourceOption = document.createElement("option");
                sourceOption.text = item.label;
                sourceOption.value = item.deviceId;
                sourceSelect.appendChild(sourceOption);
            });
        }).catch(function (reason) {
            console.log("Error ==>" + reason);
        });
    }

    initializeCameraSelection(codeReaderMain, "js_id_sh_stock_barcode_mobile_cam_select");
    initializeCameraSelection(codeReaderSource, "js_id_sh_stock_barcode_mobile_cam_select_source_location");
    initializeCameraSelection(codeReaderDestination, "js_id_sh_stock_barcode_mobile_cam_select_dest_location");

    function setupEventHandlers(codeReader, inputField, startButton, resetButton, videoElement, resultElement, selectElementId) {
        $(document).on('change', `#${selectElementId}`, function(ev) {
            var cameraSelect = $(ev.currentTarget);
            selectedDeviceId = cameraSelect.val();
            $(resetButton).click();
            $(startButton).click();
        });

        $(document).on("click", startButton, function () {
            $(inputField).val("");
            $(inputField).change();

            $(videoElement).show();
            $(resetButton).show();

            if ($('span[name="sh_stock_bm_is_cont_scan"]').text() == "True") {
                decodeContinuously(codeReader, selectedDeviceId, inputField, resultElement);
            } else {
                decodeOnce(codeReader, selectedDeviceId, inputField, resultElement, videoElement, resetButton);
            }
        });

        $(document).on("click", resetButton, function () {
            document.getElementById(resultElement).textContent = "";
            $(inputField).val("");
            $(inputField).change();

            codeReader.reset();
            $(videoElement).hide();
            $(resetButton).hide();
        });
    }

    setupEventHandlers(
        codeReaderMain,
        'input[name="sh_stock_barcode_mobile"]',
        "#js_id_sh_stock_barcode_mobile_start_btn",
        "#js_id_sh_stock_barcode_mobile_reset_btn",
        "#js_id_sh_stock_barcode_mobile_vid_div",
        "js_id_sh_stock_barcode_mobile_result",
        "js_id_sh_stock_barcode_mobile_cam_select"
    );

    setupEventHandlers(
        codeReaderSource,
        'input[name="source_location_barcode"]',
        "#js_id_sh_stock_barcode_mobile_start_btn_source_location",
        "#js_id_sh_stock_barcode_mobile_reset_btn_source_location",
        "#js_id_sh_stock_barcode_mobile_vid_div_source_location",
        "js_id_sh_stock_barcode_mobile_result_source_location",
        "js_id_sh_stock_barcode_mobile_cam_select_source_location"
    );

    setupEventHandlers(
        codeReaderDestination,
        'input[name="destination_location_barcode"]',
        "#js_id_sh_stock_barcode_mobile_start_btn_dest_location",
        "#js_id_sh_stock_barcode_mobile_reset_btn_dest_location",
        "#js_id_sh_stock_barcode_mobile_vid_div_dest_location",
        "js_id_sh_stock_barcode_mobile_result_dest_location",
        "js_id_sh_stock_barcode_mobile_cam_select_dest_location"
    );
});
